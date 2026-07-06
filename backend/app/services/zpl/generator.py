"""Generate ZPL/ZPL II from the editor's `canvas_data` tree.

This is the inverse of `parser.parse_zpl`. For imported labels it prefers
the `zpl` hints the parser stashed on each object (exact font token, exact
barcode command, field-block params) so the round-trip is faithful; for
canvas-authored objects with no hints it synthesises sensible native
commands from the geometry and the fixed font mapping.

Output is a single `^XA … ^XZ` block. Batch rendering concatenates one
block per data row (see `batch.render_batch_zpl`).
"""

from __future__ import annotations

from typing import Any

from app.services.zpl.fonts import family_to_zpl_font
from app.services.zpl.units import (
    DEFAULT_DPMM,
    mm_to_dots,
    rotation_to_orientation,
)

_ALIGN_TO_JUSTIFY = {"left": "L", "center": "C", "right": "R"}


def generate_zpl(
    canvas_data: dict[str, Any],
    *,
    dpmm: int | None = None,
    warnings: list[dict[str, Any]] | None = None,
) -> str:
    """Render `canvas_data` to a ZPL string.

    `dpmm` overrides the density; when omitted it falls back to the value
    stashed in `stage.zpl.dpmm` (set at import time) or the 203-dpi default.
    """
    stage = canvas_data.get("stage") or {}
    stage_zpl = stage.get("zpl") or {}
    if dpmm is None:
        dpmm = int(stage_zpl.get("dpmm") or DEFAULT_DPMM)

    width_mm = float(stage.get("width_mm") or 0)
    height_mm = float(stage.get("height_mm") or 0)

    out: list[str] = ["^XA"]
    out.append(f"^CI{stage_zpl.get('ci', 28)}")

    pw = stage_zpl.get("pw") or (mm_to_dots(width_mm, dpmm) if width_mm else None)
    ll = stage_zpl.get("ll") or (mm_to_dots(height_mm, dpmm) if height_mm else None)
    if pw:
        out.append(f"^PW{int(pw)}")
    if ll:
        out.append(f"^LL{int(ll)}")
    lh = stage_zpl.get("lh")
    if lh and len(lh) >= 2:
        out.append(f"^LH{int(lh[0])},{int(lh[1])}")

    for raw in stage_zpl.get("pre_raw") or []:
        out.append(str(raw))

    for obj in canvas_data.get("objects") or []:
        if obj.get("printable") is False:
            continue
        field = _emit_object(obj, dpmm, warnings)
        if field:
            out.append(field)

    for raw in stage_zpl.get("post_raw") or []:
        out.append(str(raw))

    pq = stage_zpl.get("pq")
    if pq is not None:
        out.append(f"^PQ{pq}")

    out.append("^XZ")
    return "\n".join(out)


# ------------------------------------------------------------- per object ----


def _emit_object(obj: dict[str, Any], dpmm: int, warnings: list[dict[str, Any]] | None) -> str:
    kind = obj.get("type")
    if kind == "text":
        return _emit_text(obj, dpmm)
    if kind == "barcode":
        return _emit_barcode(obj, dpmm)
    if kind == "rect":
        return _emit_rect(obj, dpmm)
    if kind == "line":
        return _emit_line(obj, dpmm)
    if kind == "table":
        return _emit_table(obj, dpmm, warnings)
    if kind == "image":
        if warnings is not None:
            warnings.append(
                {
                    "object_id": str(obj.get("id") or ""),
                    "message": "image objects can't be emitted as native ZPL; skipped",
                }
            )
        return ""
    return ""


def _fo(obj: dict[str, Any], dpmm: int, zpl_hint: dict[str, Any]) -> str:
    x = mm_to_dots(obj.get("x") or 0, dpmm)
    y = mm_to_dots(obj.get("y") or 0, dpmm)
    z = zpl_hint.get("foZ")
    return f"^FO{x},{y},{int(z)}" if z is not None else f"^FO{x},{y}"


def _emit_text(obj: dict[str, Any], dpmm: int) -> str:
    zpl_hint = obj.get("zpl") or {}
    parts = [_fo(obj, dpmm, zpl_hint)]

    orientation, _ = rotation_to_orientation(obj.get("rotation"))
    h = int(zpl_hint.get("fontHeightDots") or mm_to_dots(obj.get("fontSize") or 3, dpmm))
    w = int(zpl_hint.get("fontWidthDots") or h)

    if zpl_hint.get("builtinFont"):
        parts.append(f"^{zpl_hint['builtinFont']}{orientation},{h},{w}")
    else:
        token = zpl_hint.get("font") or family_to_zpl_font(
            obj.get("fontFamily"),
            bold=obj.get("fontWeight") == "bold",
            italic=obj.get("fontStyle") == "italic",
        )
        parts.append(f"^A@{orientation},{h},{w},{token}")

    fb = zpl_hint.get("fieldBlock")
    width_mm = obj.get("width")
    if fb or (isinstance(width_mm, int | float) and width_mm > 0):
        width_dots = mm_to_dots(width_mm or 0, dpmm) if width_mm else 0
        if fb:
            lines = int(fb.get("maxLines") or 1)
            ls = int(fb.get("lineSpacing") or 0)
            just = fb.get("justify") or _ALIGN_TO_JUSTIFY.get(obj.get("align") or "left", "L")
            hi = int(fb.get("hangIndent") or 0)
        else:
            lines, ls, hi = 1, 0, 0
            just = _ALIGN_TO_JUSTIFY.get(obj.get("align") or "left", "L")
        parts.append(f"^FB{width_dots},{lines},{ls},{just},{hi}")

    esc = zpl_hint.get("hexEscape")
    if esc:
        parts.append(f"^FH{esc if esc != '_' else ''}")
    if zpl_hint.get("reverse"):
        parts.append("^FR")

    for extra in zpl_hint.get("extra") or []:
        parts.append(str(extra))

    parts.append(f"^FD{obj.get('text') or ''}^FS")
    return "".join(parts)


# barcodeType -> factory building the native command from geometry when no
# import hint is present.
def _synth_barcode_command(obj: dict[str, Any], dpmm: int) -> str:
    bc_type = obj.get("barcodeType")
    height_dots = mm_to_dots(obj.get("height") or 15, dpmm)
    if bc_type == "qr":
        # Magnification from the box height, clamped to the ZPL 1..10 range.
        mag = max(1, min(10, round((obj.get("height") or 10) * dpmm / 25)))
        return f"^BQN,2,{mag}"
    if bc_type == "ean13":
        return f"^BEN,{height_dots},Y,N"
    # code128 / gs1_128 / gtin / ean14 → Code 128 family
    return f"^BCN,{height_dots},Y,N,N"


def _emit_barcode(obj: dict[str, Any], dpmm: int) -> str:
    zpl_hint = obj.get("zpl") or {}
    parts = [_fo(obj, dpmm, zpl_hint)]

    by = zpl_hint.get("by")
    if by:
        parts.append(f"^BY{by}")

    command = zpl_hint.get("barcodeCommand")
    if command:
        parts.append(f"^{command}{zpl_hint.get('barcodeParams', '')}")
    else:
        parts.append(_synth_barcode_command(obj, dpmm))

    for extra in zpl_hint.get("extra") or []:
        parts.append(str(extra))

    parts.append(f"^FD{obj.get('data') or ''}^FS")
    return "".join(parts)


def _emit_rect(obj: dict[str, Any], dpmm: int) -> str:
    zpl_hint = obj.get("zpl") or {}
    fo = _fo(obj, dpmm, zpl_hint)
    if zpl_hint.get("graphicParams"):
        return f"{fo}^GB{zpl_hint['graphicParams']}^FS"
    w = mm_to_dots(obj.get("width") or 0, dpmm)
    h = mm_to_dots(obj.get("height") or 0, dpmm)
    t = mm_to_dots(obj.get("strokeWidth") or 0.2, dpmm) or 1
    # A rect with a fill and no stroke is a solid block: thickness = height.
    if obj.get("fill") and not obj.get("stroke"):
        t = min(w, h)
    return f"{fo}^GB{w},{h},{t},B,0^FS"


_TABLE_PAD_MM = 0.8


def _emit_table(obj: dict[str, Any], dpmm: int, warnings: list[dict[str, Any]] | None) -> str:
    """Native table: the grid becomes ^GB boxes (thin ones act as lines) and
    every cell delegates to _emit_text as a synthetic text object, so fonts,
    ^FB wrapping and escaping stay one code path."""
    from app.services.pdf_renderer import table_col_edges

    rows = int(obj.get("rows") or 0)
    cols = int(obj.get("cols") or 0)
    w_mm = float(obj.get("width") or 0)
    h_mm = float(obj.get("height") or 0)
    if rows <= 0 or cols <= 0 or w_mm <= 0 or h_mm <= 0:
        return ""
    if float(obj.get("rotation") or 0) and warnings is not None:
        warnings.append(
            {
                "object_id": str(obj.get("id") or ""),
                "message": "table rotation isn't supported in ZPL; emitted unrotated",
            }
        )

    x_mm = float(obj.get("x") or 0)
    y_mm = float(obj.get("y") or 0)
    stroke_mm = float(obj.get("strokeWidth") or 0.2)
    t = mm_to_dots(stroke_mm, dpmm) or 1
    row_h_mm = h_mm / rows
    edges = table_col_edges(obj)
    cells = obj.get("cells") or []

    parts: list[str] = []
    x0 = mm_to_dots(x_mm, dpmm)
    y0 = mm_to_dots(y_mm, dpmm)
    w = mm_to_dots(w_mm, dpmm)
    h = mm_to_dots(h_mm, dpmm)
    parts.append(f"^FO{x0},{y0}^GB{w},{h},{t},B,0^FS")
    for col in range(1, cols):
        cx = mm_to_dots(x_mm + edges[col], dpmm)
        parts.append(f"^FO{cx},{y0}^GB{t},{h},{t},B,0^FS")
    for r in range(1, rows):
        cy = mm_to_dots(y_mm + r * row_h_mm, dpmm)
        parts.append(f"^FO{x0},{cy}^GB{w},{t},{t},B,0^FS")

    header = bool(obj.get("headerRow"))
    for r in range(rows):
        row_cells = cells[r] if r < len(cells) else []
        for col in range(cols):
            text = str(row_cells[col]) if col < len(row_cells) and row_cells[col] else ""
            if not text:
                continue
            synthetic = {
                "id": f"{obj.get('id')}-r{r}c{col}",
                "type": "text",
                "x": x_mm + edges[col] + _TABLE_PAD_MM,
                "y": y_mm + r * row_h_mm + _TABLE_PAD_MM,
                "text": text.replace("\n", " "),
                "fontSize": obj.get("fontSize") or 3,
                "fontFamily": obj.get("fontFamily"),
                "fontWeight": "bold" if header and r == 0 else obj.get("fontWeight"),
                "width": max(0.0, edges[col + 1] - edges[col] - 2 * _TABLE_PAD_MM),
            }
            parts.append(_emit_text(synthetic, dpmm))
    return "\n".join(parts)


def _emit_line(obj: dict[str, Any], dpmm: int) -> str:
    zpl_hint = obj.get("zpl") or {}
    fo = _fo(obj, dpmm, zpl_hint)
    if zpl_hint.get("graphicParams"):
        cmd = zpl_hint.get("graphic") or "GD"
        return f"{fo}^{cmd}{zpl_hint['graphicParams']}^FS"
    points = obj.get("points") or [0, 0, 0, 0]
    dx = mm_to_dots(abs(points[2] - points[0]), dpmm) if len(points) >= 4 else 0
    dy = mm_to_dots(abs(points[3] - points[1]), dpmm) if len(points) >= 4 else 0
    t = mm_to_dots(obj.get("strokeWidth") or 0.2, dpmm) or 1
    if dy == 0:
        # Horizontal rule → a thin filled box is the most reliable in ZPL.
        return f"{fo}^GB{dx},{t},{t},B,0^FS"
    if dx == 0:
        return f"{fo}^GB{t},{dy},{t},B,0^FS"
    return f"{fo}^GD{dx},{dy},{t},B,R^FS"
