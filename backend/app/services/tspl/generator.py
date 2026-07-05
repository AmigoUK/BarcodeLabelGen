"""Canvas → TSPL (TSPL2) generator for TSC / desktop Toshiba printers.

Mirrors the ZPL generator's object walk but emits TSPL commands. Coordinates
are dots (origin top-left); millimetres convert through the shared dpmm math.
Font sizing is approximate — TSPL built-in fonts are bitmap fonts scaled by
integer multipliers, unlike the editor's TrueType fonts.
"""

from __future__ import annotations

from typing import Any

from app.services.zpl.units import DEFAULT_DPMM, mm_to_dots

# TSPL built-in bitmap fonts: name -> approx glyph height in dots at
# multiplier 1 (common TSC values; used only to choose the closest
# font+multiplier for a requested height — real metrics vary by model).
_TSPL_FONTS: list[tuple[str, int]] = [
    ("1", 12),
    ("2", 16),
    ("3", 24),
    ("4", 32),
    ("5", 48),
    ("8", 60),
]

_ALLOWED_ROT = (0, 90, 180, 270)

# canvas barcodeType -> TSPL BARCODE code_type
_BARCODE_TYPE: dict[str, str] = {
    "code128": "128",
    "gtin": "128",
    "ean14": "128",
    "gs1_128": "EAN128",
    "ean13": "EAN13",
}

_TABLE_PAD_MM = 0.8


def _fmt_mm(value: float) -> str:
    return f"{float(value):g}"


def _esc(text: Any) -> str:  # noqa: ANN401
    # TSPL strings are double-quoted; embed a literal quote via the \[22] code
    # (22 = ASCII double-quote). Backslashes stay literal.
    return str(text if text is not None else "").replace('"', "\\[22]")


def _snap_rot(rotation: float | None, warnings: list[dict] | None, obj_id: str) -> int:
    deg = round(float(rotation or 0)) % 360
    if deg in _ALLOWED_ROT:
        return deg
    nearest = min(_ALLOWED_ROT, key=lambda a: min(abs(a - deg), 360 - abs(a - deg)))
    if warnings is not None:
        warnings.append(
            {
                "object_id": obj_id,
                "message": f"rotation {deg}° snapped to {nearest}° (TSPL supports 0/90/180/270)",
            }
        )
    return nearest


def _pick_font(
    font_size_mm: float | None, dpmm: int, warnings: list[dict] | None, obj_id: str
) -> tuple[str, int]:
    target = mm_to_dots(font_size_mm or 3, dpmm)
    best_name, best_mul, best_err = "3", 1, None
    for name, base in _TSPL_FONTS:
        mul = max(1, round(target / base)) if base else 1
        err = abs(base * mul - target)
        if best_err is None or err < best_err:
            best_name, best_mul, best_err = name, mul, err
    if warnings is not None and target > 0 and best_err is not None and best_err > 0.25 * target:
        warnings.append(
            {"object_id": obj_id, "message": "TSPL bitmap fonts approximate the editor font size"}
        )
    return best_name, best_mul


def generate_tspl(
    canvas_data: dict[str, Any],
    *,
    dpmm: int | None = None,
    warnings: list[dict[str, Any]] | None = None,
) -> str:
    """Render `canvas_data` to a TSPL string."""
    stage = canvas_data.get("stage") or {}
    stage_zpl = stage.get("zpl") or {}
    if dpmm is None:
        dpmm = int(stage_zpl.get("dpmm") or DEFAULT_DPMM)

    width_mm = float(stage.get("width_mm") or 0)
    height_mm = float(stage.get("height_mm") or 0)

    out: list[str] = []
    if width_mm > 0 and height_mm > 0:
        out.append(f"SIZE {_fmt_mm(width_mm)} mm, {_fmt_mm(height_mm)} mm")
    elif warnings is not None:
        warnings.append(
            {
                "object_id": "",
                "message": "label size missing; SIZE omitted (printer uses its own calibration)",
            }
        )
    out.append("GAP 3 mm, 0 mm")
    out.append("DIRECTION 1")
    out.append("REFERENCE 0,0")
    out.append("CLS")

    for obj in canvas_data.get("objects") or []:
        if obj.get("printable") is False:
            continue
        line = _emit_object(obj, dpmm, warnings)
        if line:
            out.append(line)

    pq = stage_zpl.get("pq")
    try:
        copies = int(pq) if pq is not None else 1
    except (TypeError, ValueError):
        copies = 1  # pq can be a printer-variable string like "{NoLabel}"
    out.append(f"PRINT {copies}")
    return "\n".join(out)


def _emit_object(obj: dict[str, Any], dpmm: int, warnings: list[dict] | None) -> str:
    kind = obj.get("type")
    if kind == "text":
        return _emit_text(obj, dpmm, warnings)
    if kind == "barcode":
        return _emit_barcode(obj, dpmm, warnings)
    if kind == "rect":
        return _emit_rect(obj, dpmm)
    if kind == "line":
        return _emit_line(obj, dpmm, warnings)
    if kind == "table":
        return _emit_table(obj, dpmm, warnings)
    if kind == "image":
        if warnings is not None:
            warnings.append(
                {
                    "object_id": str(obj.get("id") or ""),
                    "message": "image objects can't be emitted as native TSPL; skipped",
                }
            )
        return ""
    return ""


def _emit_text(obj: dict[str, Any], dpmm: int, warnings: list[dict] | None) -> str:
    obj_id = str(obj.get("id") or "")
    x = mm_to_dots(obj.get("x") or 0, dpmm)
    y = mm_to_dots(obj.get("y") or 0, dpmm)
    rot = _snap_rot(obj.get("rotation"), warnings, obj_id)
    font, mul = _pick_font(obj.get("fontSize"), dpmm, warnings, obj_id)
    text = _esc(obj.get("text"))
    width_mm = obj.get("width")
    if isinstance(width_mm, int | float) and width_mm > 0:
        w = mm_to_dots(width_mm, dpmm)
        h = mm_to_dots(obj.get("height") or (obj.get("fontSize") or 3), dpmm)
        return f'BLOCK {x},{y},{w},{h},"{font}",{rot},{mul},{mul},"{text}"'
    return f'TEXT {x},{y},"{font}",{rot},{mul},{mul},"{text}"'


def _emit_barcode(obj: dict[str, Any], dpmm: int, warnings: list[dict] | None) -> str:
    obj_id = str(obj.get("id") or "")
    x = mm_to_dots(obj.get("x") or 0, dpmm)
    y = mm_to_dots(obj.get("y") or 0, dpmm)
    rot = _snap_rot(obj.get("rotation"), warnings, obj_id)
    data = _esc(obj.get("data"))
    bc = obj.get("barcodeType")
    if bc == "qr":
        cell = max(1, min(10, round((obj.get("height") or 10) * dpmm / 25)))
        return f'QRCODE {x},{y},M,{cell},A,{rot},"{data}"'
    tspl_type = _BARCODE_TYPE.get(bc)
    if tspl_type is None:
        tspl_type = "128"
        if warnings is not None:
            warnings.append(
                {"object_id": obj_id, "message": f"barcode type {bc!r} not mapped; used Code 128"}
            )
    h = mm_to_dots(obj.get("height") or 15, dpmm)
    return f'BARCODE {x},{y},"{tspl_type}",{h},1,{rot},2,2,"{data}"'


def _emit_rect(obj: dict[str, Any], dpmm: int) -> str:
    x = mm_to_dots(obj.get("x") or 0, dpmm)
    y = mm_to_dots(obj.get("y") or 0, dpmm)
    w = mm_to_dots(obj.get("width") or 0, dpmm)
    h = mm_to_dots(obj.get("height") or 0, dpmm)
    # A filled rect with no stroke is a solid block.
    if obj.get("fill") and not obj.get("stroke"):
        return f"BAR {x},{y},{w},{h}"
    t = mm_to_dots(obj.get("strokeWidth") or 0.2, dpmm) or 1
    return f"BOX {x},{y},{x + w},{y + h},{t}"


def _emit_line(obj: dict[str, Any], dpmm: int, warnings: list[dict] | None) -> str:
    x = mm_to_dots(obj.get("x") or 0, dpmm)
    y = mm_to_dots(obj.get("y") or 0, dpmm)
    points = obj.get("points") or [0, 0, 0, 0]
    dx = mm_to_dots(abs(points[2] - points[0]), dpmm) if len(points) >= 4 else 0
    dy = mm_to_dots(abs(points[3] - points[1]), dpmm) if len(points) >= 4 else 0
    t = mm_to_dots(obj.get("strokeWidth") or 0.2, dpmm) or 1
    if dy == 0:
        return f"BAR {x},{y},{dx or t},{t}"
    if dx == 0:
        return f"BAR {x},{y},{t},{dy}"
    if warnings is not None:
        warnings.append(
            {
                "object_id": str(obj.get("id") or ""),
                "message": "diagonal lines aren't supported in TSPL; skipped",
            }
        )
    return ""


def _emit_table(obj: dict[str, Any], dpmm: int, warnings: list[dict] | None) -> str:
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
                "message": "table rotation isn't supported in TSPL; emitted unrotated",
            }
        )

    x_mm = float(obj.get("x") or 0)
    y_mm = float(obj.get("y") or 0)
    t = mm_to_dots(float(obj.get("strokeWidth") or 0.2), dpmm) or 1
    row_h_mm = h_mm / rows
    edges = table_col_edges(obj)
    cells = obj.get("cells") or []

    parts: list[str] = []
    x0 = mm_to_dots(x_mm, dpmm)
    y0 = mm_to_dots(y_mm, dpmm)
    w = mm_to_dots(w_mm, dpmm)
    h = mm_to_dots(h_mm, dpmm)
    parts.append(f"BOX {x0},{y0},{x0 + w},{y0 + h},{t}")
    for col in range(1, cols):
        cx = mm_to_dots(x_mm + edges[col], dpmm)
        parts.append(f"BAR {cx},{y0},{t},{h}")
    for r in range(1, rows):
        cy = mm_to_dots(y_mm + r * row_h_mm, dpmm)
        parts.append(f"BAR {x0},{cy},{w},{t}")

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
                "width": max(0.0, edges[col + 1] - edges[col] - 2 * _TABLE_PAD_MM),
            }
            parts.append(_emit_text(synthetic, dpmm, warnings))
    return "\n".join(parts)
