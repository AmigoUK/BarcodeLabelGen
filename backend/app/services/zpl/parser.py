"""Parse a ZPL/ZPL II label into the editor's `canvas_data` tree.

Scope: the command subset that maps cleanly onto the canvas object model
(text, barcode, rect, line) plus the label-level framing. Anything we
don't model is preserved verbatim as passthrough so a round-trip never
silently drops content:

  * unrecognised commands *outside* a field  → stage.zpl.pre_raw / post_raw
  * unrecognised commands *inside* a field    → object.zpl.extra
  * a whole field we can't classify           → a raw passthrough block

Placeholders (`{NAZWA}`, `{EAN}`, `^PQ{NoLabel}`) are treated as opaque
text and kept 1:1 — filling them is the job of the downstream system (or,
for `{{column}}` syntax, the batch renderer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.zpl.fonts import zpl_font_to_family
from app.services.zpl.units import DEFAULT_DPMM, dots_to_mm, orientation_to_rotation

# Label-level commands hoisted out of field context wherever they appear.
_LABEL_COMMANDS = {"CI", "PW", "LL", "LH", "PQ"}
# Framing / no-op commands consumed silently.
_FRAME_COMMANDS = {"XA", "XZ"}

# Fallback stage size (mm) when the label carries no ^PW / ^LL.
_DEFAULT_WIDTH_MM = 100.0
_DEFAULT_HEIGHT_MM = 150.0


@dataclass
class _Token:
    prefix: str  # '^' or '~'
    code: str  # 2-char command code, upper-cased (e.g. 'FO', 'A@', 'BQ')
    params: str  # raw parameter string (verbatim for ^FD, stripped otherwise)

    def render(self) -> str:
        return f"{self.prefix}{self.code}{self.params}"


def tokenize(zpl: str) -> list[_Token]:
    """Split a ZPL stream into command tokens.

    A command is a caret/tilde marker, a 2-character code, then parameters
    running to the next marker. `^FD` (field data) keeps its parameters
    verbatim; every other command has surrounding whitespace/newlines
    stripped (ZPL ignores newlines between commands, but they are literal
    inside field data).
    """
    markers = [i for i, ch in enumerate(zpl) if ch in "^~"]
    tokens: list[_Token] = []
    for idx, start in enumerate(markers):
        prefix = zpl[start]
        code = zpl[start + 1 : start + 3].upper()
        end = markers[idx + 1] if idx + 1 < len(markers) else len(zpl)
        params = zpl[start + 3 : end]
        if code != "FD":
            params = params.strip()
        tokens.append(_Token(prefix, code, params))
    return tokens


@dataclass
class _StageMeta:
    ci: int | None = None
    pw: int | None = None
    ll: int | None = None
    lh: list[int] | None = None
    pq: str | None = None
    pre_raw: list[str] = field(default_factory=list)
    post_raw: list[str] = field(default_factory=list)


def _split_params(params: str) -> list[str]:
    return [p.strip() for p in params.split(",")]


def _num(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def parse_zpl(zpl: str, dpmm: int = DEFAULT_DPMM) -> dict[str, Any]:
    """Parse `zpl` into `{"canvas_data": {...}, "warnings": [...]}`.

    `dpmm` (dots per mm) drives the dots→mm conversion; pass the value that
    matches the target printhead (8 for 203 dpi, 12 for 300 dpi).
    """
    tokens = tokenize(zpl)
    stage = _StageMeta()
    objects: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    seen_object = False  # routes label-level raw to pre_ vs post_raw

    current: list[_Token] = []
    for tok in tokens:
        if tok.code in _FRAME_COMMANDS:
            continue
        if tok.code == "FS":
            # Field closes — classify what we accumulated.
            obj = _build_object(current, dpmm, warnings)
            if obj is not None:
                objects.append(obj)
                seen_object = True
            elif current:
                raw = "".join(t.render() for t in current) + "^FS"
                (stage.post_raw if seen_object else stage.pre_raw).append(raw)
            current = []
            continue
        if tok.code in _LABEL_COMMANDS and not current:
            _apply_label_command(tok, stage)
            continue
        if tok.code in _LABEL_COMMANDS and current:
            # e.g. ^CI28 sitting inside a field — hoist to label level but
            # keep the field otherwise intact.
            _apply_label_command(tok, stage)
            continue
        current.append(tok)

    # A trailing field with no ^FS (some generators omit the last one).
    if current:
        obj = _build_object(current, dpmm, warnings)
        if obj is not None:
            objects.append(obj)
        else:
            raw = "".join(t.render() for t in current)
            (stage.post_raw if seen_object else stage.pre_raw).append(raw)

    for i, obj in enumerate(objects):
        obj["id"] = f"zpl-{i}"

    width_mm = dots_to_mm(stage.pw, dpmm) if stage.pw else _DEFAULT_WIDTH_MM
    height_mm = dots_to_mm(stage.ll, dpmm) if stage.ll else _DEFAULT_HEIGHT_MM
    if not stage.pw or not stage.ll:
        warnings.append(
            {
                "object_id": "",
                "message": "label had no ^PW/^LL; stage size defaulted — adjust as needed",
            }
        )

    stage_zpl: dict[str, Any] = {"dpmm": dpmm, "ci": stage.ci if stage.ci is not None else 28}
    if stage.pw is not None:
        stage_zpl["pw"] = stage.pw
    if stage.ll is not None:
        stage_zpl["ll"] = stage.ll
    if stage.lh is not None:
        stage_zpl["lh"] = stage.lh
    if stage.pq is not None:
        stage_zpl["pq"] = stage.pq
    if stage.pre_raw:
        stage_zpl["pre_raw"] = stage.pre_raw
    if stage.post_raw:
        stage_zpl["post_raw"] = stage.post_raw

    canvas_data = {
        "version": 1,
        "stage": {
            "width_mm": round(width_mm, 3),
            "height_mm": round(height_mm, 3),
            "zpl": stage_zpl,
        },
        "objects": objects,
    }
    return {"canvas_data": canvas_data, "warnings": warnings}


def _apply_label_command(tok: _Token, stage: _StageMeta) -> None:
    if tok.code == "CI":
        stage.ci = int(_num(tok.params, 28))
    elif tok.code == "PW":
        stage.pw = int(_num(_split_params(tok.params)[0], 0)) or None
    elif tok.code == "LL":
        stage.ll = int(_num(_split_params(tok.params)[0], 0)) or None
    elif tok.code == "LH":
        parts = _split_params(tok.params)
        stage.lh = [int(_num(parts[0], 0)), int(_num(parts[1], 0)) if len(parts) > 1 else 0]
    elif tok.code == "PQ":
        stage.pq = tok.params


# ---------------------------------------------------------------- fields ----


def _find(tokens: list[_Token], *codes: str) -> _Token | None:
    for t in tokens:
        if t.code in codes:
            return t
    return None


def _is_barcode_code(code: str) -> bool:
    # ZPL barcode commands are ^B followed by a letter/digit (BC, BE, BQ,
    # B8, B7, B3, BX…). ^BY is the *default* setter, not a barcode itself.
    return len(code) == 2 and code[0] == "B" and code != "BY"


def _build_object(
    tokens: list[_Token], dpmm: int, warnings: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Classify a field's tokens into one canvas object, or None if the
    field can't be modelled (caller preserves it as raw passthrough)."""
    if not tokens:
        return None

    fo = _find(tokens, "FO", "FT")
    x_mm = y_mm = 0.0
    fo_z: int | None = None
    if fo is not None:
        parts = _split_params(fo.params)
        x_mm = dots_to_mm(_num(parts[0]) if parts else 0, dpmm)
        y_mm = dots_to_mm(_num(parts[1]) if len(parts) > 1 else 0, dpmm)
        if len(parts) > 2 and parts[2] != "":
            fo_z = int(_num(parts[2]))

    barcode_tok = next((t for t in tokens if _is_barcode_code(t.code)), None)
    if barcode_tok is not None:
        return _build_barcode(tokens, barcode_tok, x_mm, y_mm, fo_z, dpmm)

    font_tok = _find(tokens, "A@") or next(
        (t for t in tokens if t.code.startswith("A") and t.code not in {"A@"}), None
    )
    fd_tok = _find(tokens, "FD")
    if fd_tok is not None or font_tok is not None:
        return _build_text(tokens, font_tok, fd_tok, x_mm, y_mm, fo_z, dpmm, warnings)

    gb_tok = _find(tokens, "GB")
    if gb_tok is not None:
        return _build_box(gb_tok, x_mm, y_mm, fo_z, dpmm)

    gd_tok = _find(tokens, "GD")
    if gd_tok is not None:
        return _build_diagonal(gd_tok, x_mm, y_mm, dpmm)

    return None


_MODELLED_TEXT_CODES = {"FO", "FT", "A@", "FB", "FH", "FD", "FR"}


def _build_text(
    tokens: list[_Token],
    font_tok: _Token | None,
    fd_tok: _Token | None,
    x_mm: float,
    y_mm: float,
    fo_z: int | None,
    dpmm: int,
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    zpl_hint: dict[str, Any] = {}
    rotation = 0
    font_h_dots = 0
    font_w_dots = 0
    family, weight, style = "Arial", "normal", "normal"

    if font_tok is not None:
        parts = _split_params(font_tok.params)
        orientation = parts[0] if parts and parts[0] else "N"
        rotation = orientation_to_rotation(orientation)
        if len(parts) > 1:
            font_h_dots = int(_num(parts[1]))
        if len(parts) > 2:
            font_w_dots = int(_num(parts[2]))
        if font_tok.code == "A@" and len(parts) > 3:
            token = parts[3]
            family, weight, style = zpl_font_to_family(token)
            zpl_hint["font"] = token
        else:
            # Built-in font ^A0..^A9 — record the code so we can re-emit it.
            zpl_hint["builtinFont"] = font_tok.code
        zpl_hint["fontHeightDots"] = font_h_dots
        if font_w_dots:
            zpl_hint["fontWidthDots"] = font_w_dots
        zpl_hint["orientation"] = orientation

    font_size_mm = dots_to_mm(font_h_dots, dpmm) if font_h_dots else 3.0

    obj: dict[str, Any] = {
        "id": "",
        "type": "text",
        "x": round(x_mm, 3),
        "y": round(y_mm, 3),
        "text": fd_tok.params if fd_tok is not None else "",
        "fontSize": round(font_size_mm, 3),
        "fontFamily": family,
        "fill": "#000000",
    }
    if weight == "bold":
        obj["fontWeight"] = "bold"
    if style == "italic":
        obj["fontStyle"] = "italic"
    if rotation:
        obj["rotation"] = rotation

    fb_tok = _find(tokens, "FB")
    if fb_tok is not None:
        parts = _split_params(fb_tok.params)
        if parts and parts[0]:
            obj["width"] = round(dots_to_mm(_num(parts[0]), dpmm), 3)
        just = parts[3].upper() if len(parts) > 3 and parts[3] else "L"
        obj["align"] = {"L": "left", "C": "center", "R": "right", "J": "left"}.get(just, "left")
        zpl_hint["fieldBlock"] = {
            "maxLines": int(_num(parts[1])) if len(parts) > 1 and parts[1] else 1,
            "lineSpacing": int(_num(parts[2])) if len(parts) > 2 and parts[2] else 0,
            "justify": just,
            "hangIndent": int(_num(parts[4])) if len(parts) > 4 and parts[4] else 0,
        }

    fh_tok = _find(tokens, "FH")
    if fh_tok is not None:
        zpl_hint["hexEscape"] = fh_tok.params or "_"

    if _find(tokens, "FR") is not None:
        zpl_hint["reverse"] = True

    if fo_z is not None:
        zpl_hint["foZ"] = fo_z

    extra = [t.render() for t in tokens if t.code not in _MODELLED_TEXT_CODES]
    if extra:
        zpl_hint["extra"] = extra

    if zpl_hint:
        obj["zpl"] = zpl_hint
    return obj


_MODELLED_BARCODE_CODES = {"FO", "FT", "BY", "FD", "FR"}

# ZPL barcode command -> our barcodeType (best-effort; params kept in hint).
_BARCODE_TYPE_MAP: dict[str, str] = {
    "BQ": "qr",
    "BC": "code128",
    "BE": "ean13",
    "B8": "ean13",  # EAN-8 has no canvas equivalent; nearest linear
    "BX": "qr",  # Datamatrix → nearest 2D
}


def _build_barcode(
    tokens: list[_Token],
    barcode_tok: _Token,
    x_mm: float,
    y_mm: float,
    fo_z: int | None,
    dpmm: int,
) -> dict[str, Any]:
    zpl_hint: dict[str, Any] = {
        "barcodeCommand": barcode_tok.code,
        "barcodeParams": barcode_tok.params,
    }
    bc_type = _BARCODE_TYPE_MAP.get(barcode_tok.code, "code128")
    fd_tok = _find(tokens, "FD")

    by_tok = _find(tokens, "BY")
    if by_tok is not None:
        zpl_hint["by"] = by_tok.params

    # Display size (mm). Native barcode sizing is data-dependent, so these
    # are best-effort boxes for on-canvas dragging; the exact command lives
    # in the hint and drives the actual output.
    if bc_type == "qr":
        parts = _split_params(barcode_tok.params)
        magnification = int(_num(parts[2])) if len(parts) > 2 and parts[2] else 3
        # ~25 modules for a short payload; good enough to grab and move.
        side_mm = dots_to_mm(magnification * 25, dpmm)
        width_mm = height_mm = round(side_mm, 3)
    else:
        parts = _split_params(barcode_tok.params)
        height_dots = int(_num(parts[1])) if len(parts) > 1 and parts[1] else 0
        if not height_dots and by_tok is not None:
            by_parts = _split_params(by_tok.params)
            height_dots = int(_num(by_parts[2])) if len(by_parts) > 2 and by_parts[2] else 0
        height_mm = round(dots_to_mm(height_dots or 80, dpmm), 3)
        width_mm = round(max(20.0, height_mm * 2), 3)

    if fo_z is not None:
        zpl_hint["foZ"] = fo_z

    extra = [t.render() for t in tokens if t.code not in _MODELLED_BARCODE_CODES]
    # The barcode command itself is captured in the hint, so drop it from extra.
    extra = [e for e in extra if not e.startswith(barcode_tok.prefix + barcode_tok.code)]
    if extra:
        zpl_hint["extra"] = extra

    return {
        "id": "",
        "type": "barcode",
        "x": round(x_mm, 3),
        "y": round(y_mm, 3),
        "width": width_mm,
        "height": height_mm,
        "barcodeType": bc_type,
        "data": fd_tok.params if fd_tok is not None else "",
        "zpl": zpl_hint,
    }


def _build_box(
    gb_tok: _Token, x_mm: float, y_mm: float, fo_z: int | None, dpmm: int
) -> dict[str, Any]:
    parts = _split_params(gb_tok.params)
    w_dots = _num(parts[0]) if parts else 0
    h_dots = _num(parts[1]) if len(parts) > 1 else 0
    t_dots = _num(parts[2]) if len(parts) > 2 and parts[2] else 1
    zpl_hint: dict[str, Any] = {"graphic": "GB", "graphicParams": gb_tok.params}
    if fo_z is not None:
        zpl_hint["foZ"] = fo_z
    return {
        "id": "",
        "type": "rect",
        "x": round(x_mm, 3),
        "y": round(y_mm, 3),
        "width": round(dots_to_mm(w_dots, dpmm), 3),
        "height": round(dots_to_mm(h_dots, dpmm), 3),
        "fill": "",
        "stroke": "#000000",
        "strokeWidth": round(dots_to_mm(t_dots, dpmm), 3),
        "zpl": zpl_hint,
    }


def _build_diagonal(gd_tok: _Token, x_mm: float, y_mm: float, dpmm: int) -> dict[str, Any]:
    parts = _split_params(gd_tok.params)
    w_dots = _num(parts[0]) if parts else 0
    h_dots = _num(parts[1]) if len(parts) > 1 else 0
    t_dots = _num(parts[2]) if len(parts) > 2 and parts[2] else 1
    return {
        "id": "",
        "type": "line",
        "x": round(x_mm, 3),
        "y": round(y_mm, 3),
        "points": [0, 0, round(dots_to_mm(w_dots, dpmm), 3), round(dots_to_mm(h_dots, dpmm), 3)],
        "stroke": "#000000",
        "strokeWidth": round(dots_to_mm(t_dots, dpmm), 3),
        "zpl": {"graphic": "GD", "graphicParams": gd_tok.params},
    }
