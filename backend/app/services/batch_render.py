"""Multi-page PDF rendering with {{column}} substitution.

Each row in the dataset produces one page; placeholders in text content
and barcode `data` fields are replaced with that row's values. Rows with
unrenderable barcode data (after substitution) still emit a page, just
with the bad object skipped — same resilience policy as single-label.
"""

from __future__ import annotations

import io
import re
from collections.abc import Callable, Iterable
from copy import deepcopy
from typing import Any

from reportlab.lib.colors import HexColor  # noqa: F401  — re-exported for parity
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

from app.models.asset import Asset
from app.services.pdf_renderer import (
    _draw_barcode,
    _draw_image,
    _draw_line,
    _draw_rect,
    _draw_text,
)
from app.services.placeholders import evaluate_date_key, is_plain_date_key

PLACEHOLDER_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")

AssetResolver = Callable[[int], Asset | None]
ProgressCallback = Callable[[int, int], None]


def substitute_string(value: str, row: dict[str, Any]) -> str:
    """Replace every {{column}} occurrence with row's value (str-cast).

    Date placeholders ({{date}}, {{date+14d:DD/MM/YY}}, …) are computed at
    render time; a dataset column literally named `date` still wins for the
    plain {{date}} form, offset/format forms are always computed."""

    def repl(m: re.Match[str]) -> str:
        key = m.group(1).strip()
        computed = evaluate_date_key(key)
        if computed is not None and not (is_plain_date_key(key) and key in row):
            return computed
        return "" if key not in row else str(row[key])

    return PLACEHOLDER_RE.sub(repl, value)


def substitute_object(obj: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of `obj` with {{column}} substituted in any
    field that the renderer reads. We don't mutate the input — callers
    keep the original template intact across rows."""
    out = dict(obj)
    kind = out.get("type")
    if kind == "text" and isinstance(out.get("text"), str):
        out["text"] = substitute_string(out["text"], row)
    elif kind == "barcode" and isinstance(out.get("data"), str):
        out["data"] = substitute_string(out["data"], row)
    return out


def render_batch_pdf(
    canvas_data: dict[str, Any],
    rows: Iterable[dict[str, Any]],
    *,
    width_mm: float,
    height_mm: float,
    resolve_asset: AssetResolver | None = None,
    on_progress: ProgressCallback | None = None,
    warnings: list[dict[str, Any]] | None = None,
) -> bytes:
    """Render one page per row, substituting placeholders. Returns PDF bytes.

    `warnings`, if provided, gets a per-row entry annotated with the row
    index for any text-block that overflowed at its minimum font size.
    """
    base_objects = canvas_data.get("objects") or []
    page_size = (width_mm * mm, height_mm * mm)

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=page_size)
    page_h_pt = height_mm * mm

    rows_list = list(rows)
    total = len(rows_list)
    if total == 0:
        # Still emit a blank page so callers always get a valid PDF
        c.showPage()
        c.save()
        return buf.getvalue()

    for i, row in enumerate(rows_list):
        # Re-apply default colours each page so per-page state is clean
        c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0, 0, 0)

        # Per-row warnings buffer — annotated with the row index after
        # rendering this page, then merged into the global accumulator.
        row_warnings: list[dict[str, Any]] = [] if warnings is not None else []

        for obj in base_objects:
            # Skip reference-only (printable=False) objects — same rule
            # as the single-label renderer.
            if obj.get("printable") is False:
                continue
            substituted = substitute_object(deepcopy(obj), row)
            try:
                kind = substituted.get("type")
                if kind == "text":
                    _draw_text(c, substituted, page_h_pt, warnings=row_warnings)
                elif kind == "rect":
                    _draw_rect(c, substituted, page_h_pt)
                elif kind == "line":
                    _draw_line(c, substituted, page_h_pt)
                elif kind == "image":
                    _draw_image(c, substituted, page_h_pt, resolve_asset)
                elif kind == "barcode":
                    _draw_barcode(c, substituted, page_h_pt)
            except Exception:  # noqa: BLE001, S112 — per-object resilience
                continue

        if warnings is not None and row_warnings:
            for w in row_warnings:
                warnings.append({**w, "row": i + 1})  # 1-indexed for humans

        c.showPage()
        if on_progress is not None:
            on_progress(i + 1, total)

    c.save()
    return buf.getvalue()
