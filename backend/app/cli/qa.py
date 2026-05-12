# mypy: ignore-errors
"""QA harness: build calibration templates, render PDFs, measure positions.

Run inside the container:
    docker compose exec web flask qa-templates

Creates a fixed set of "QA: <format>" templates owned by the seeded admin.
Each template lays known-position markers near every edge plus a centred
barcode. Renders one PDF per template via the same render_template_pdf
service the user-facing endpoint uses, then opens each PDF with
pdfplumber and compares the actual element positions to the expected
ones (in millimetres). Prints a pass/fail report with worst-case
deviations.

mypy is disabled here on purpose: the per-section measurement loops
reuse `best`/`exp` for different dataclass types, and the cleanest
strictly-typed alternative would triple the file length without any
real safety win for a one-off calibration tool.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click
import pdfplumber
from flask import Flask
from flask.cli import with_appcontext
from sqlalchemy import select

from app.db.session import get_session
from app.models.label_format import FormatKind, LabelFormat
from app.models.template import Template
from app.models.user import Role, User
from app.services.pdf_renderer import render_template_pdf

# Tolerance for declaring a position "correct". 0.5 mm is tighter than
# what a Zebra printer can hit and well within visual perception.
TOLERANCE_MM = 0.5

# Where rendered PDFs land. /tmp by default so the script doesn't litter
# the production pdfs volume; --keep flag overrides.
DEFAULT_OUTPUT_DIR = Path("/tmp/blg_qa")

QA_NAME_PREFIX = "QA: "


# --- expected-element bookkeeping ----------------------------------------


@dataclass
class ExpectedRect:
    label: str
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float


@dataclass
class ExpectedLine:
    label: str
    # Absolute mm: from (x1,y1) to (x2,y2) on the page (top-left origin).
    x1_mm: float
    y1_mm: float
    x2_mm: float
    y2_mm: float


@dataclass
class ExpectedText:
    label: str
    x_mm: float
    y_mm: float  # TOP of the bounding box, not baseline
    text: str
    font_size_mm: float


@dataclass
class ExpectedBarcode:
    label: str
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float


@dataclass
class TemplateSpec:
    width_mm: float
    height_mm: float
    canvas: dict[str, Any]
    expected_rects: list[ExpectedRect] = field(default_factory=list)
    expected_lines: list[ExpectedLine] = field(default_factory=list)
    expected_texts: list[ExpectedText] = field(default_factory=list)
    expected_barcodes: list[ExpectedBarcode] = field(default_factory=list)


# --- canvas builder ------------------------------------------------------


def build_qa_template(width_mm: float, height_mm: float) -> TemplateSpec:
    """Build a calibration canvas + the expected-positions manifest.

    Layout (in mm, top-left origin):
      - Inner border rect 1 mm from each edge
      - 4×4 mm filled square at each corner, 2 mm from edges
      - Single-character text marker next to each corner square
      - Horizontal line near top edge (y=2 mm) and bottom edge
        (y=height-2 mm)
      - Vertical line near left edge (x=2 mm) and right edge
        (x=width-2 mm)
      - Centered Code-128 barcode "QA-OK" if the label is big enough
    """
    objs: list[dict[str, Any]] = []
    rects: list[ExpectedRect] = []
    lines: list[ExpectedLine] = []
    texts: list[ExpectedText] = []
    barcodes: list[ExpectedBarcode] = []

    # 1. Inner border rect
    border_x, border_y = 1.0, 1.0
    border_w, border_h = width_mm - 2.0, height_mm - 2.0
    objs.append(
        {
            "id": "border",
            "type": "rect",
            "x": border_x,
            "y": border_y,
            "width": border_w,
            "height": border_h,
            "fill": "#ffffff",  # transparent fill not supported; use white
            "stroke": "#000000",
            "strokeWidth": 0.2,
        }
    )
    rects.append(ExpectedRect("border", border_x, border_y, border_w, border_h))

    # 2. Corner-marker squares
    marker = 4.0  # mm
    edge_pad = 2.0
    corners = [
        ("TL", edge_pad, edge_pad),
        ("TR", width_mm - edge_pad - marker, edge_pad),
        ("BL", edge_pad, height_mm - edge_pad - marker),
        ("BR", width_mm - edge_pad - marker, height_mm - edge_pad - marker),
    ]
    for label, x, y in corners:
        rid = f"corner_{label}"
        objs.append(
            {
                "id": rid,
                "type": "rect",
                "x": x,
                "y": y,
                "width": marker,
                "height": marker,
                "fill": "#000000",
                "stroke": "#000000",
                "strokeWidth": 0.0,
            }
        )
        rects.append(ExpectedRect(rid, x, y, marker, marker))

    # 3. Edge lines (anchor at 0,0 with absolute points)
    edge_inset = 2.0
    line_specs = [
        (
            "edge_top",
            edge_inset + marker + 1,
            edge_inset,
            width_mm - edge_inset - marker - 1,
            edge_inset,
        ),
        (
            "edge_bottom",
            edge_inset + marker + 1,
            height_mm - edge_inset,
            width_mm - edge_inset - marker - 1,
            height_mm - edge_inset,
        ),
        (
            "edge_left",
            edge_inset,
            edge_inset + marker + 1,
            edge_inset,
            height_mm - edge_inset - marker - 1,
        ),
        (
            "edge_right",
            width_mm - edge_inset,
            edge_inset + marker + 1,
            width_mm - edge_inset,
            height_mm - edge_inset - marker - 1,
        ),
    ]
    for lid, x1, y1, x2, y2 in line_specs:
        objs.append(
            {
                "id": lid,
                "type": "line",
                "x": x1,
                "y": y1,
                "points": [0, 0, x2 - x1, y2 - y1],
                "stroke": "#0066cc",
                "strokeWidth": 0.3,
            }
        )
        lines.append(ExpectedLine(lid, x1, y1, x2, y2))

    # 4. Centered barcode (skip for tiny labels where it wouldn't fit)
    bc_w = min(40.0, width_mm * 0.6)
    bc_h = min(15.0, height_mm * 0.3)
    if bc_w >= 25.0 and bc_h >= 8.0:
        bc_x = (width_mm - bc_w) / 2
        bc_y = (height_mm - bc_h) / 2
        objs.append(
            {
                "id": "center_barcode",
                "type": "barcode",
                "barcodeType": "code128",
                "data": "QA-OK",
                "x": bc_x,
                "y": bc_y,
                "width": bc_w,
                "height": bc_h,
            }
        )
        barcodes.append(ExpectedBarcode("center_barcode", bc_x, bc_y, bc_w, bc_h))

    # 5. Corner text labels (one ASCII character each, easy to find)
    text_size_mm = 2.5
    text_offset = marker + 1.5
    text_specs = [
        ("text_TL", edge_pad + text_offset, edge_pad, "T"),
        ("text_TR", width_mm - edge_pad - marker - text_offset, edge_pad, "U"),
        ("text_BL", edge_pad + text_offset, height_mm - edge_pad - text_size_mm, "B"),
        (
            "text_BR",
            width_mm - edge_pad - marker - text_offset,
            height_mm - edge_pad - text_size_mm,
            "X",
        ),
    ]
    for tid, x, y, char in text_specs:
        objs.append(
            {
                "id": tid,
                "type": "text",
                "x": x,
                "y": y,
                "text": char,
                "fontSize": text_size_mm,
                "fontFamily": "Helvetica",
                "fill": "#000000",
            }
        )
        texts.append(ExpectedText(tid, x, y, char, text_size_mm))

    canvas = {
        "version": 1,
        "stage": {"width_mm": width_mm, "height_mm": height_mm},
        "objects": objs,
    }
    return TemplateSpec(
        width_mm=width_mm,
        height_mm=height_mm,
        canvas=canvas,
        expected_rects=rects,
        expected_lines=lines,
        expected_texts=texts,
        expected_barcodes=barcodes,
    )


# --- measurement ---------------------------------------------------------


@dataclass
class CheckResult:
    label: str
    expected: str
    actual: str
    deviation_mm: float
    passed: bool


def _pt_to_mm(pt: float) -> float:
    return pt / 2.834645669


def _measure_pdf(pdf_path: Path, spec: TemplateSpec) -> list[CheckResult]:
    """Open the rendered PDF and check every expected element."""
    results: list[CheckResult] = []
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            results.append(CheckResult("page", "1 page", "no pages", float("inf"), False))
            return results
        page = pdf.pages[0]

        # Page size sanity check
        actual_w_mm = _pt_to_mm(page.width)
        actual_h_mm = _pt_to_mm(page.height)
        page_dev = max(abs(actual_w_mm - spec.width_mm), abs(actual_h_mm - spec.height_mm))
        results.append(
            CheckResult(
                "page_size",
                f"{spec.width_mm:.1f}×{spec.height_mm:.1f} mm",
                f"{actual_w_mm:.2f}×{actual_h_mm:.2f} mm",
                page_dev,
                page_dev <= TOLERANCE_MM,
            )
        )

        # --- rectangles ---
        # pdfplumber returns rects with top/left in points, top-left origin.
        for exp in spec.expected_rects:
            # Find the rect whose centre is closest to the expected centre.
            exp_cx = exp.x_mm + exp.w_mm / 2
            exp_cy = exp.y_mm + exp.h_mm / 2
            best = None
            best_dev = float("inf")
            for r in page.rects:
                cx = _pt_to_mm((r["x0"] + r["x1"]) / 2)
                cy = _pt_to_mm((r["top"] + r["bottom"]) / 2)
                w = _pt_to_mm(r["x1"] - r["x0"])
                h = _pt_to_mm(r["bottom"] - r["top"])
                pos_dev = max(abs(cx - exp_cx), abs(cy - exp_cy))
                size_dev = max(abs(w - exp.w_mm), abs(h - exp.h_mm))
                dev = max(pos_dev, size_dev)
                if dev < best_dev:
                    best_dev = dev
                    best = (cx, cy, w, h)
            results.append(
                CheckResult(
                    f"rect:{exp.label}",
                    f"({exp.x_mm:.1f},{exp.y_mm:.1f}) {exp.w_mm:.1f}×{exp.h_mm:.1f}",
                    (
                        f"({best[0] - best[2] / 2:.2f},{best[1] - best[3] / 2:.2f}) "
                        f"{best[2]:.2f}×{best[3]:.2f}"
                        if best
                        else "—"
                    ),
                    best_dev,
                    best_dev <= TOLERANCE_MM,
                )
            )

        # --- lines ---
        # pdfplumber sees lines as edges with x0/top/x1/bottom in points.
        for exp in spec.expected_lines:
            best = None
            best_dev = float("inf")
            for ln in page.edges:
                if ln.get("orientation") not in ("h", "v"):
                    continue
                lx1 = _pt_to_mm(ln["x0"])
                ly1 = _pt_to_mm(ln["top"])
                lx2 = _pt_to_mm(ln["x1"])
                ly2 = _pt_to_mm(ln["bottom"])
                # Compare endpoint pairs in either direction
                d_forward = max(
                    abs(lx1 - exp.x1_mm),
                    abs(ly1 - exp.y1_mm),
                    abs(lx2 - exp.x2_mm),
                    abs(ly2 - exp.y2_mm),
                )
                d_reverse = max(
                    abs(lx1 - exp.x2_mm),
                    abs(ly1 - exp.y2_mm),
                    abs(lx2 - exp.x1_mm),
                    abs(ly2 - exp.y1_mm),
                )
                dev = min(d_forward, d_reverse)
                if dev < best_dev:
                    best_dev = dev
                    best = (lx1, ly1, lx2, ly2)
            results.append(
                CheckResult(
                    f"line:{exp.label}",
                    f"({exp.x1_mm:.1f},{exp.y1_mm:.1f}) → ({exp.x2_mm:.1f},{exp.y2_mm:.1f})",
                    (
                        f"({best[0]:.2f},{best[1]:.2f}) → ({best[2]:.2f},{best[3]:.2f})"
                        if best
                        else "—"
                    ),
                    best_dev,
                    best_dev <= TOLERANCE_MM,
                )
            )

        # --- text characters ---
        for exp in spec.expected_texts:
            # pdfplumber's chars list includes positioned glyphs.
            matches = [c for c in page.chars if c.get("text") == exp.text]
            if not matches:
                results.append(
                    CheckResult(
                        f"text:{exp.label}",
                        f"({exp.x_mm:.1f},{exp.y_mm:.1f}) “{exp.text}”",
                        "missing",
                        float("inf"),
                        False,
                    )
                )
                continue
            # Pick the char whose top-left is closest to expected
            best = None
            best_dev = float("inf")
            for ch in matches:
                cx = _pt_to_mm(ch["x0"])
                cy = _pt_to_mm(ch["top"])
                dev = max(abs(cx - exp.x_mm), abs(cy - exp.y_mm))
                if dev < best_dev:
                    best_dev = dev
                    best = (cx, cy)
            results.append(
                CheckResult(
                    f"text:{exp.label}",
                    f"({exp.x_mm:.1f},{exp.y_mm:.1f}) “{exp.text}”",
                    (f"({best[0]:.2f},{best[1]:.2f}) “{exp.text}”" if best else "—"),
                    best_dev,
                    best_dev <= TOLERANCE_MM,
                )
            )

        # --- barcodes (rendered as embedded images) ---
        for exp in spec.expected_barcodes:
            best = None
            best_dev = float("inf")
            for img in page.images:
                ix = _pt_to_mm(img["x0"])
                iy = _pt_to_mm(img["top"])
                iw = _pt_to_mm(img["x1"] - img["x0"])
                ih = _pt_to_mm(img["bottom"] - img["top"])
                pos_dev = max(abs(ix - exp.x_mm), abs(iy - exp.y_mm))
                size_dev = max(abs(iw - exp.w_mm), abs(ih - exp.h_mm))
                dev = max(pos_dev, size_dev)
                if dev < best_dev:
                    best_dev = dev
                    best = (ix, iy, iw, ih)
            results.append(
                CheckResult(
                    f"barcode:{exp.label}",
                    f"({exp.x_mm:.1f},{exp.y_mm:.1f}) {exp.w_mm:.1f}×{exp.h_mm:.1f}",
                    (
                        f"({best[0]:.2f},{best[1]:.2f}) {best[2]:.2f}×{best[3]:.2f}"
                        if best
                        else "missing"
                    ),
                    best_dev,
                    best_dev <= TOLERANCE_MM,
                )
            )

    return results


# --- CLI -----------------------------------------------------------------


def _ensure_qa_owner(session: Any) -> User:
    """Reuse the seeded admin if present; otherwise pick any admin or
    fall back to creating a synthetic QA owner."""
    user = session.execute(select(User).where(User.email == "admin@blg.local")).scalar_one_or_none()
    if user:
        return user
    user = session.execute(
        select(User).where(User.role == Role.ADMIN).limit(1)
    ).scalar_one_or_none()
    if user:
        return user
    raise RuntimeError("No admin user found — run `flask seed-admin` first")


@click.command("qa-templates")
@click.option(
    "--output-dir",
    default=str(DEFAULT_OUTPUT_DIR),
    show_default=True,
    help="Where rendered PDFs are written.",
)
@click.option("--clean/--no-clean", default=True, help="Remove existing QA templates first.")
@with_appcontext
def qa_templates(output_dir: str, clean: bool) -> None:
    """Build calibration templates, render PDFs, measure positions."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    session = get_session()
    owner = _ensure_qa_owner(session)

    if clean:
        deleted = (
            session.query(Template)
            .filter(Template.name.like(f"{QA_NAME_PREFIX}%"))
            .delete(synchronize_session=False)
        )
        session.commit()
        if deleted:
            click.echo(f"🧹 cleaned {deleted} previous QA template(s)")

    formats = (
        session.execute(
            select(LabelFormat)
            .where(LabelFormat.kind != FormatKind.CUSTOM)
            .order_by(LabelFormat.id)
        )
        .scalars()
        .all()
    )
    if not formats:
        raise click.ClickException("No label formats in DB — run migrations first")

    overall_pass = True
    for fmt in formats:
        spec = build_qa_template(float(fmt.width_mm), float(fmt.height_mm))
        tpl = Template(
            owner_id=owner.id,
            name=f"{QA_NAME_PREFIX}{fmt.name}",
            description=f"Calibration template for {fmt.name}",
            format_id=fmt.id,
            width_mm=spec.width_mm,
            height_mm=spec.height_mm,
            canvas_data=spec.canvas,
        )
        session.add(tpl)
        session.commit()
        session.refresh(tpl)

        # Render PDF
        pdf_bytes = render_template_pdf(
            spec.canvas,
            width_mm=spec.width_mm,
            height_mm=spec.height_mm,
        )
        safe_name = (
            fmt.name.replace(" ", "_")
            .replace("/", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("×", "x")
            .replace('"', "in")
        )
        pdf_path = output / f"qa_{safe_name}.pdf"
        pdf_path.write_bytes(pdf_bytes)

        # Measure
        results = _measure_pdf(pdf_path, spec)
        n_pass = sum(1 for r in results if r.passed)
        n_total = len(results)
        all_pass = n_pass == n_total
        if not all_pass:
            overall_pass = False

        symbol = "✅" if all_pass else "❌"
        click.echo(
            f"\n{symbol} {fmt.name}  "
            f"({spec.width_mm:.1f}×{spec.height_mm:.1f} mm)  "
            f"{n_pass}/{n_total} checks passed  "
            f"→ {pdf_path}"
        )
        if not all_pass:
            for r in results:
                if not r.passed:
                    click.echo(
                        f"   ❌ {r.label:24s}  "
                        f"expected {r.expected:42s}  "
                        f"actual {r.actual:42s}  "
                        f"Δ={r.deviation_mm:.2f} mm"
                    )
        else:
            # Show worst deviation per format even when passing — useful
            # to track regressions over time.
            worst = max(results, key=lambda r: r.deviation_mm)
            click.echo(f"   worst Δ {worst.deviation_mm:.2f} mm ({worst.label})")

    click.echo("\n" + ("✅ ALL CHECKS PASSED" if overall_pass else "❌ SOME CHECKS FAILED"))
    if not overall_pass:
        os._exit(1)


def register_qa_cli(app: Flask) -> None:
    app.cli.add_command(qa_templates)
