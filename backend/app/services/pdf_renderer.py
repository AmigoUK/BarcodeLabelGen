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
) -> bytes:
    """Render `canvas_data` to a single-page PDF and return raw bytes.

    `resolve_asset` is a callable taking an asset id and returning an Asset
    instance (or None) — injected by the route layer so this function stays
    decoupled from Flask/SQLAlchemy.
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
        try:
            kind = obj.get("type")
            if kind == "text":
                _draw_text(c, obj, page_h_pt)
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


def _draw_text(c: rl_canvas.Canvas, obj: dict[str, Any], page_h_pt: float) -> None:
    text = str(obj.get("text") or "")
    if not text:
        return
    x_mm = float(obj.get("x") or 0)
    y_mm = float(obj.get("y") or 0)
    font_size_mm = float(obj.get("fontSize") or 4)
    fill = _hex_to_rgb(obj.get("fill")) or HexColor("#000000")
    align = obj.get("align") or "left"
    bold = obj.get("fontWeight") == "bold"
    italic = obj.get("fontStyle") == "italic"
    rotation = float(obj.get("rotation") or 0)

    # ReportLab's built-in PostScript fonts cover Latin-1; Polish letters
    # in Helvetica work because ReportLab maps to ISO-8859-2 / WinAnsi.
    base = "Helvetica"
    if bold and italic:
        font = f"{base}-BoldOblique"
    elif bold:
        font = f"{base}-Bold"
    elif italic:
        font = f"{base}-Oblique"
    else:
        font = base

    font_size_pt = font_size_mm * mm  # actually mm → pt via the same scale
    # Convert mm font size to "pt" the way ReportLab expects: setFont takes
    # a point size. 1 mm = 2.834 pt, so multiplying by `mm` is correct.

    c.saveState()
    c.setFillColor(fill)
    c.setFont(font, font_size_pt)

    # In Konva, the y is the TOP of the text bounding box. ReportLab's
    # drawString places the BASELINE. Approximate baseline = top + font_size
    # (this works for single-line text; multi-line wrap is a Sprint 5+ task).
    x_pt = x_mm * mm
    baseline_y_pt = page_h_pt - (y_mm * mm) - font_size_pt * 0.85

    if rotation:
        # Rotate around the top-left anchor so behaviour matches the editor
        c.translate(x_pt, page_h_pt - y_mm * mm)
        c.rotate(-rotation)
        c.translate(-x_pt, -(page_h_pt - y_mm * mm))

    for i, line in enumerate(text.split("\n")):
        line_y = baseline_y_pt - i * font_size_pt * 1.2
        if align == "center":
            c.drawCentredString(x_pt + (float(obj.get("width") or 0) * mm) / 2, line_y, line)
        elif align == "right":
            c.drawRightString(x_pt + (float(obj.get("width") or 0) * mm), line_y, line)
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
