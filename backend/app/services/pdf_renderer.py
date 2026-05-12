"""Render a canvas_data tree to a single-page PDF via ReportLab.

The canvas tree is authored in millimetres; ReportLab's coordinate
system uses PDF points (1 pt = 1/72 inch ≈ 0.3528 mm) with the origin
at the BOTTOM-LEFT corner of the page. Konva's origin is top-left.
The renderer handles both conversions in one pass.

For Sprint 4 this renders a single label as a single page. Sprint 5
will reuse this same function in a loop over CSV rows.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas

from app.models.asset import Asset
from app.services.assets import assets_dir
from app.services.barcodes import (
    BarcodeRenderError,
    BarcodeType,
    normalize_data,
    render_png,
)

# Injected by the route layer so this module stays free of Flask/SQLAlchemy.
AssetResolver = Callable[[int], Asset | None]


class PdfRenderError(ValueError):
    pass


def render_template_pdf(
    canvas_data: dict[str, Any],
    *,
    width_mm: float,
    height_mm: float,
    resolve_asset: AssetResolver | None = None,
    warnings: list[dict[str, Any]] | None = None,
) -> bytes:
    """Render `canvas_data` to a single-page PDF and return raw bytes.

    `resolve_asset` is a callable taking an asset id and returning an Asset
    instance (or None) — injected by the route layer so this function stays
    decoupled from Flask/SQLAlchemy.

    `warnings`, if provided, is appended to with `{"object_id", "message"}`
    entries for soft-failure cases (currently: text-block overflow at the
    minimum font size). The PDF is still produced, just truncated.
    """
    if not isinstance(canvas_data, dict):
        raise PdfRenderError("canvas_data must be a dict")
    objects = canvas_data.get("objects") or []

    buf = io.BytesIO()
    page_size = (width_mm * mm, height_mm * mm)
    c = rl_canvas.Canvas(buf, pagesize=page_size)
    # Default fill/stroke
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0, 0, 0)

    page_h_pt = height_mm * mm

    for obj in objects:
        # Reference-only objects (e.g. a background image used to align
        # text against a pre-printed logo) are flagged printable=False
        # in the editor; the renderer skips them entirely so the user
        # gets only the new content in the PDF, not a double-print.
        if obj.get("printable") is False:
            continue
        try:
            kind = obj.get("type")
            if kind == "text":
                _draw_text(c, obj, page_h_pt, warnings=warnings)
            elif kind == "rect":
                _draw_rect(c, obj, page_h_pt)
            elif kind == "line":
                _draw_line(c, obj, page_h_pt)
            elif kind == "image":
                _draw_image(c, obj, page_h_pt, resolve_asset)
            elif kind == "barcode":
                _draw_barcode(c, obj, page_h_pt)
            else:
                # Unknown object types are skipped silently rather than crash
                # the whole render. Future schema additions stay backwards
                # compatible this way.
                continue
        except (PdfRenderError, BarcodeRenderError):
            # Per-object failures shouldn't sink the whole PDF; we just skip.
            # If a later iteration of UX wants to surface them, the caller
            # can wrap this loop instead.
            continue

    c.showPage()
    c.save()
    return buf.getvalue()


# ---------- per-object renderers ----------


def _hex_to_rgb(value: str | None) -> HexColor | None:
    if not value:
        return None
    try:
        return HexColor(value)
    except (ValueError, AttributeError):
        return None


def _y_flip(top_y_mm: float, height_mm: float, page_h_pt: float) -> float:
    """Konva: y is the TOP edge from page top. ReportLab: y is the BOTTOM
    edge from page bottom. Convert with the object's height baked in."""
    return float(page_h_pt - (top_y_mm + height_mm) * mm)


# Helvetica's ascent is ~71.8 % of the font size; the same ratio is close
# enough for Times/Courier at label sizes that we don't bother per-family.
_ASCENT_RATIO = 0.718
_LINE_HEIGHT_FACTOR = 1.2


def _resolve_font(obj: dict[str, Any]) -> str:
    """Map the user-facing font family to one of ReportLab's standard PDF
    fonts (no embedding needed). Inter/Arial/Helvetica are visually
    indistinguishable at label sizes; same for Times/Georgia."""
    family = (obj.get("fontFamily") or "").lower()
    bold = obj.get("fontWeight") == "bold"
    italic = obj.get("fontStyle") == "italic"
    if "courier" in family:
        base = "Courier"
        styles = ("", "-Bold", "-Oblique", "-BoldOblique")
    elif "times" in family or "georgia" in family or "serif" in family:
        base = "Times"
        styles = ("-Roman", "-Bold", "-Italic", "-BoldItalic")
    else:
        base = "Helvetica"
        styles = ("", "-Bold", "-Oblique", "-BoldOblique")
    idx = (1 if bold else 0) + (2 if italic else 0)
    return f"{base}{styles[idx]}"


def _wrap_lines(text: str, font: str, font_size_pt: float, max_width_pt: float) -> list[str]:
    """Greedy word-wrap honouring explicit \\n breaks. Words longer than
    max_width are kept on their own line (overflow is detected later by
    the caller measuring each returned line's width)."""
    out: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        if not words:
            out.append("")
            continue
        current = words[0]
        for w in words[1:]:
            candidate = f"{current} {w}"
            if stringWidth(candidate, font, font_size_pt) <= max_width_pt:
                current = candidate
            else:
                out.append(current)
                current = w
        out.append(current)
    return out


def _layout_fits(
    lines: list[str],
    font: str,
    font_size_pt: float,
    max_width_pt: float,
    max_height_pt: float,
) -> bool:
    """True if `lines` fits inside the given box (no per-line wider than
    max_width and total height under max_height)."""
    total_h = len(lines) * font_size_pt * _LINE_HEIGHT_FACTOR
    if total_h > max_height_pt:
        return False
    return all(stringWidth(line, font, font_size_pt) <= max_width_pt for line in lines)


def _autofit_size_pt(
    text: str,
    font: str,
    max_width_pt: float,
    max_height_pt: float,
    min_size_pt: float,
    max_size_pt: float,
) -> tuple[float, list[str], bool]:
    """Find the largest font size in [min, max] (0.5 pt steps) that lets
    `text` fit inside the box after word-wrapping. Falls back to min_size
    if nothing fits — caller logs a warning in that case.

    Returns (chosen_size_pt, wrapped_lines, fits_cleanly).
    """
    step = 0.5  # pt — fine enough to feel smooth, coarse enough to be cheap
    size = max_size_pt
    while size >= min_size_pt:
        lines = _wrap_lines(text, font, size, max_width_pt)
        if _layout_fits(lines, font, size, max_width_pt, max_height_pt):
            return size, lines, True
        size -= step
    # Nothing fit — render at minimum and report
    final_lines = _wrap_lines(text, font, min_size_pt, max_width_pt)
    return min_size_pt, final_lines, False


def _draw_text(
    c: rl_canvas.Canvas,
    obj: dict[str, Any],
    page_h_pt: float,
    *,
    warnings: list[dict[str, Any]] | None = None,
) -> None:
    text = str(obj.get("text") or "")
    if not text:
        return
    x_mm = float(obj.get("x") or 0)
    y_mm = float(obj.get("y") or 0)
    font_size_mm = float(obj.get("fontSize") or 4)
    fill = _hex_to_rgb(obj.get("fill")) or HexColor("#000000")
    align = obj.get("align") or "left"
    rotation = float(obj.get("rotation") or 0)

    width_raw = obj.get("width")
    has_explicit_width = isinstance(width_raw, int | float) and width_raw > 0
    width_mm_value = (
        float(width_raw) if isinstance(width_raw, int | float) and width_raw > 0 else 0.0
    )

    height_raw = obj.get("height")
    has_explicit_height = isinstance(height_raw, int | float) and height_raw > 0
    height_mm_value = (
        float(height_raw) if isinstance(height_raw, int | float) and height_raw > 0 else 0.0
    )

    # Konva semantics:
    #  - no width            → single line, no wrap
    #  - width only          → wrap-at-width (height grows with content)
    #  - width + height      → bounded box; auto-fit shrinks font if asked
    # We mirror those three modes here so the PDF lays text out the same
    # way the editor preview does — otherwise a centred wrap-at-width text
    # would be a single overflowing line in the PDF and visibly drift
    # left of the wrap box.
    font = _resolve_font(obj)
    has_box = has_explicit_width and has_explicit_height
    has_wrap_only = has_explicit_width and not has_explicit_height

    if has_box and obj.get("autoFit"):
        max_width_pt = width_mm_value * mm
        max_height_pt = height_mm_value * mm
        min_pt = float(obj.get("minFontSize") or font_size_mm) * mm
        max_pt = float(obj.get("maxFontSize") or font_size_mm) * mm
        min_pt, max_pt = (min(min_pt, max_pt), max(min_pt, max_pt))
        font_size_pt, lines, fits = _autofit_size_pt(
            text, font, max_width_pt, max_height_pt, min_pt, max_pt
        )
        if not fits and warnings is not None:
            warnings.append(
                {
                    "object_id": str(obj.get("id") or ""),
                    "message": (
                        f"text didn't fit at minimum font size {min_pt / mm:.1f} mm; truncated"
                    ),
                }
            )
    elif has_box:
        max_width_pt = width_mm_value * mm
        max_height_pt = height_mm_value * mm
        font_size_pt = font_size_mm * mm
        lines = _wrap_lines(text, font, font_size_pt, max_width_pt)
        if warnings is not None and not _layout_fits(
            lines, font, font_size_pt, max_width_pt, max_height_pt
        ):
            warnings.append(
                {
                    "object_id": str(obj.get("id") or ""),
                    "message": (
                        f"text didn't fit at {font_size_mm:.1f} mm; "
                        "enable auto-fit or enlarge the box"
                    ),
                }
            )
    elif has_wrap_only:
        max_width_pt = width_mm_value * mm
        font_size_pt = font_size_mm * mm
        lines = _wrap_lines(text, font, font_size_pt, max_width_pt)
    else:
        font_size_pt = font_size_mm * mm
        lines = text.split("\n")

    c.saveState()
    c.setFillColor(fill)
    c.setFont(font, font_size_pt)

    # In Konva, y is the TOP of the text bounding box. ReportLab's
    # drawString puts the BASELINE at y. Helvetica's ascent is ~71.8 % of
    # the font size, so baseline = top + 0.718*size.
    x_pt = x_mm * mm
    baseline_y_pt = page_h_pt - (y_mm * mm) - font_size_pt * _ASCENT_RATIO

    if rotation:
        c.translate(x_pt, page_h_pt - y_mm * mm)
        c.rotate(-rotation)
        c.translate(-x_pt, -(page_h_pt - y_mm * mm))

    for i, line in enumerate(lines):
        line_y = baseline_y_pt - i * font_size_pt * _LINE_HEIGHT_FACTOR

        # Centering/right-aligning only makes sense when the text has an
        # explicit `width` (the wrap box). Without it, Konva lays out
        # left-aligned regardless of the `align` value — so do the same.
        if align == "center" and has_explicit_width:
            c.drawCentredString(x_pt + (width_mm_value * mm) / 2, line_y, line)
        elif align == "right" and has_explicit_width:
            c.drawRightString(x_pt + (width_mm_value * mm), line_y, line)
        else:
            c.drawString(x_pt, line_y, line)

    c.restoreState()


def _draw_rect(c: rl_canvas.Canvas, obj: dict[str, Any], page_h_pt: float) -> None:
    x_mm = float(obj.get("x") or 0)
    y_mm = float(obj.get("y") or 0)
    w_mm = float(obj.get("width") or 0)
    h_mm = float(obj.get("height") or 0)
    if w_mm <= 0 or h_mm <= 0:
        return
    fill = _hex_to_rgb(obj.get("fill"))
    stroke = _hex_to_rgb(obj.get("stroke"))
    stroke_w_mm = float(obj.get("strokeWidth") or 0)
    rotation = float(obj.get("rotation") or 0)

    c.saveState()
    if fill:
        c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
    c.setLineWidth(stroke_w_mm * mm)

    x_pt = x_mm * mm
    y_pt = _y_flip(y_mm, h_mm, page_h_pt)

    if rotation:
        c.translate(x_pt, page_h_pt - y_mm * mm)
        c.rotate(-rotation)
        c.translate(-x_pt, -(page_h_pt - y_mm * mm))

    c.rect(
        x_pt,
        y_pt,
        w_mm * mm,
        h_mm * mm,
        stroke=1 if stroke and stroke_w_mm > 0 else 0,
        fill=1 if fill else 0,
    )
    c.restoreState()


def _draw_line(c: rl_canvas.Canvas, obj: dict[str, Any], page_h_pt: float) -> None:
    x_mm = float(obj.get("x") or 0)
    y_mm = float(obj.get("y") or 0)
    points = obj.get("points") or []
    if len(points) < 4 or len(points) % 2 != 0:
        return
    stroke = _hex_to_rgb(obj.get("stroke")) or HexColor("#000000")
    stroke_w_mm = float(obj.get("strokeWidth") or 0.2)
    rotation = float(obj.get("rotation") or 0)

    c.saveState()
    c.setStrokeColor(stroke)
    c.setLineWidth(stroke_w_mm * mm)
    c.setLineCap(1)  # round caps to match Konva's lineCap="round"

    anchor_x_pt = x_mm * mm
    anchor_y_pt = page_h_pt - y_mm * mm  # anchor in PDF space (no flip yet)

    if rotation:
        c.translate(anchor_x_pt, anchor_y_pt)
        c.rotate(-rotation)
        c.translate(-anchor_x_pt, -anchor_y_pt)

    path = c.beginPath()
    px0 = anchor_x_pt + float(points[0]) * mm
    py0 = anchor_y_pt - float(points[1]) * mm
    path.moveTo(px0, py0)
    for i in range(2, len(points), 2):
        px = anchor_x_pt + float(points[i]) * mm
        py = anchor_y_pt - float(points[i + 1]) * mm
        path.lineTo(px, py)
    c.drawPath(path, stroke=1, fill=0)
    c.restoreState()


def _draw_image(
    c: rl_canvas.Canvas,
    obj: dict[str, Any],
    page_h_pt: float,
    resolve_asset: AssetResolver | None,
) -> None:
    asset_id = obj.get("assetId")
    if not isinstance(asset_id, int) or resolve_asset is None:
        return
    asset = resolve_asset(asset_id)
    if asset is None:
        return

    file_path = assets_dir() / asset.storage_filename
    if not file_path.is_file():
        return

    x_mm = float(obj.get("x") or 0)
    y_mm = float(obj.get("y") or 0)
    w_mm = float(obj.get("width") or 10)
    h_mm = float(obj.get("height") or 10)
    rotation = float(obj.get("rotation") or 0)

    c.saveState()
    x_pt = x_mm * mm
    y_pt = _y_flip(y_mm, h_mm, page_h_pt)

    if rotation:
        c.translate(x_pt, page_h_pt - y_mm * mm)
        c.rotate(-rotation)
        c.translate(-x_pt, -(page_h_pt - y_mm * mm))

    c.drawImage(
        str(file_path),
        x_pt,
        y_pt,
        width=w_mm * mm,
        height=h_mm * mm,
        preserveAspectRatio=False,
        mask="auto",
    )
    c.restoreState()


def _draw_barcode(c: rl_canvas.Canvas, obj: dict[str, Any], page_h_pt: float) -> None:
    bc_type_raw = obj.get("barcodeType")
    data = str(obj.get("data") or "")
    if not bc_type_raw or not data:
        return
    try:
        bc_type = BarcodeType(bc_type_raw)
    except ValueError:
        return
    data = normalize_data(bc_type, data)
    w_mm = float(obj.get("width") or 30)
    h_mm = float(obj.get("height") or 15)

    # Render to PNG, then drop into the PDF as an image. This keeps a
    # single rendering pipeline (the same bytes the editor shows on screen
    # land in the PDF), avoiding double-implementation drift between
    # preview and print.
    png_bytes = render_png(bc_type, data, width_mm=w_mm, height_mm=h_mm)

    x_mm = float(obj.get("x") or 0)
    y_mm = float(obj.get("y") or 0)
    rotation = float(obj.get("rotation") or 0)

    c.saveState()
    x_pt = x_mm * mm
    y_pt = _y_flip(y_mm, h_mm, page_h_pt)

    if rotation:
        c.translate(x_pt, page_h_pt - y_mm * mm)
        c.rotate(-rotation)
        c.translate(-x_pt, -(page_h_pt - y_mm * mm))

    # ReportLab's ImageReader accepts a BytesIO of PNG bytes directly.
    c.drawImage(
        ImageReader(io.BytesIO(png_bytes)),
        x_pt,
        y_pt,
        width=w_mm * mm,
        height=h_mm * mm,
        preserveAspectRatio=False,
        mask="auto",
    )
    c.restoreState()
