# F22 — TSPL Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users export the editor canvas as TSPL (for TSC / desktop Toshiba printers), mirroring the existing ZPL export: a new `tspl/` generator, a `POST /api/tspl/generate` endpoint, and an "Export TSPL" editor modal.

**Architecture:** A new backend package `app/services/tspl/` exposes `generate_tspl(canvas_data, *, dpmm, warnings)` that walks the same canvas objects as the ZPL generator and emits TSPL commands (SIZE/GAP/DIRECTION/CLS … PRINT). It reuses the generic `mm→dots` math from `app.services.zpl.units` and leaves `zpl/` untouched. A new blueprint mirrors the ZPL endpoint's single-label ("template") mode; the frontend adds a TSPL export modal mirroring `ExportZplModal`.

**Tech Stack:** Python 3.12 + Flask + Pydantic + pytest (backend, verifiable here); React + TS + react-query (frontend, typecheck/lint here).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-05-f22-tspl-export-design.md`. Variant A, single-label MVP.
- **Do not modify `app/services/zpl/`** — TSPL reuses `mm_to_dots`, `DEFAULT_DPMM` from `app.services.zpl.units` by import only.
- Target language is **TSPL/TSPL2** (TSC / desktop Toshiba). TPCL, agent-printing, batch, and round-trip are OUT OF SCOPE.
- `generate_tspl(canvas_data, *, dpmm=None, warnings=None) -> str` — same `dpmm`/`warnings` semantics as `generate_zpl`. `dpmm` falls back to `stage.zpl.dpmm` or `DEFAULT_DPMM`.
- TSPL output shape: `SIZE <w> mm, <h> mm` / `GAP 3 mm, 0 mm` / `DIRECTION 1` / `REFERENCE 0,0` / `CLS` / <objects> / `PRINT <copies>`. Coordinates in dots, origin top-left. Copies from `stage.zpl.pq` else 1.
- Object mapping: text→`TEXT` (width>0 → `BLOCK`); barcode code128/gtin/ean14→`"128"`, gs1_128→`"EAN128"`, ean13→`"EAN13"` via `BARCODE`; qr→`QRCODE`; rect outline→`BOX`, filled rect / line→`BAR`; table→grid `BAR` + cell `TEXT`; image→skip + warning; unknown barcode→`"128"` + warning; rotation snapped to 0/90/180/270 + warning when snapped.
- Warnings are dicts `{"object_id": str, "message": str}` (same shape as ZPL warnings).
- Endpoint mirrors the ZPL `mode="template"` branch: attachment `.txt`, `text/plain; charset=utf-8`, `Cache-Control: no-store`, warnings in `X-TSPL-Warnings` + `Access-Control-Expose-Headers`.
- Version bump app `0.19.1 → 0.20.0`. Commit trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Backend gate: `ruff check` + `pytest` clean. Frontend gate: `npm run typecheck` + `npm run lint` clean.

---

### Task 1: TSPL generator (`app/services/tspl/`)

**Files:**
- Create: `backend/app/services/tspl/__init__.py`
- Create: `backend/app/services/tspl/generator.py`
- Test: `backend/tests/test_tspl.py`

**Interfaces:**
- Consumes: `mm_to_dots`, `DEFAULT_DPMM` from `app.services.zpl.units`; `table_col_edges` from `app.services.pdf_renderer`.
- Produces: `generate_tspl(canvas_data: dict, *, dpmm: int | None = None, warnings: list[dict] | None = None) -> str`. Task 2 (endpoint) calls it.

- [ ] **Step 1: Write `backend/app/services/tspl/generator.py`**

```python
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


def _esc(text: Any) -> str:
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
                "width": max(0.0, edges[col + 1] - edges[col] - 2 * _TABLE_PAD_MM),
            }
            parts.append(_emit_text(synthetic, dpmm, warnings))
    return "\n".join(parts)
```

- [ ] **Step 2: Write `backend/app/services/tspl/__init__.py`**

```python
"""Canvas → TSPL export engine.

Public surface:
  * `generate_tspl(canvas, *, dpmm, warnings)` — canvas → TSPL text
"""

from __future__ import annotations

from app.services.tspl.generator import generate_tspl

__all__ = ["generate_tspl"]
```

- [ ] **Step 3: Write `backend/tests/test_tspl.py`**

```python
"""Structural tests for the canvas → TSPL generator."""

from __future__ import annotations

from app.services.tspl import generate_tspl

_STAGE = {"stage": {"width_mm": 50, "height_mm": 30, "zpl": {"dpmm": 8}}}


def _gen(objects, warnings=None, **stage_extra):
    data = {"stage": dict(_STAGE["stage"], **stage_extra), "objects": objects}
    return generate_tspl(data, warnings=warnings)


def test_header_and_footer():
    out = _gen([])
    lines = out.splitlines()
    assert lines[0] == "SIZE 50 mm, 30 mm"
    assert "GAP 3 mm, 0 mm" in lines
    assert "DIRECTION 1" in lines
    assert "CLS" in lines
    assert lines[-1] == "PRINT 1"


def test_copies_from_pq_numeric():
    data = {"stage": {"width_mm": 50, "height_mm": 30, "zpl": {"dpmm": 8, "pq": 3}}, "objects": []}
    assert generate_tspl(data).splitlines()[-1] == "PRINT 3"


def test_copies_pq_variable_falls_back_to_one():
    data = {
        "stage": {"width_mm": 50, "height_mm": 30, "zpl": {"dpmm": 8, "pq": "{NoLabel}"}},
        "objects": [],
    }
    assert generate_tspl(data).splitlines()[-1] == "PRINT 1"


def test_missing_size_warns_and_omits():
    warnings = []
    data = {"stage": {"zpl": {"dpmm": 8}}, "objects": []}
    out = generate_tspl(data, warnings=warnings)
    assert not any(line.startswith("SIZE") for line in out.splitlines())
    assert any("SIZE omitted" in w["message"] for w in warnings)


def test_text_emits_TEXT():
    out = _gen([{"type": "text", "x": 5, "y": 10, "fontSize": 3, "text": "Hi"}])
    assert 'TEXT 40,80,"' in out
    assert out.rstrip().endswith('"Hi"')


def test_text_with_width_emits_BLOCK():
    out = _gen([{"type": "text", "x": 0, "y": 0, "width": 20, "fontSize": 3, "text": "wrap"}])
    assert "BLOCK 0,0,160," in out


def test_text_escapes_quote():
    out = _gen([{"type": "text", "x": 0, "y": 0, "fontSize": 3, "text": 'a"b'}])
    assert 'a\\[22]b' in out


def test_barcode_code128():
    out = _gen([{"type": "barcode", "x": 2, "y": 2, "barcodeType": "code128", "height": 10, "data": "ABC"}])
    assert 'BARCODE 16,16,"128",80,1,0,2,2,"ABC"' in out


def test_barcode_ean13():
    out = _gen([{"type": "barcode", "x": 0, "y": 0, "barcodeType": "ean13", "height": 10, "data": "590"}])
    assert '"EAN13"' in out


def test_barcode_gs1_128():
    out = _gen([{"type": "barcode", "x": 0, "y": 0, "barcodeType": "gs1_128", "height": 10, "data": "X"}])
    assert '"EAN128"' in out


def test_barcode_unknown_warns_and_falls_back():
    warnings = []
    out = _gen([{"type": "barcode", "x": 0, "y": 0, "barcodeType": "pdf417", "height": 10, "data": "X"}], warnings)
    assert '"128"' in out
    assert any("not mapped" in w["message"] for w in warnings)


def test_qr_emits_QRCODE():
    out = _gen([{"type": "barcode", "x": 1, "y": 1, "barcodeType": "qr", "height": 12, "data": "url"}])
    assert out.count("QRCODE 8,8,M,") == 1
    assert out.rstrip().endswith('"url"')


def test_rect_outline_emits_BOX():
    out = _gen([{"type": "rect", "x": 1, "y": 1, "width": 10, "height": 5, "stroke": "#000", "strokeWidth": 0.5}])
    # x0=8,y0=8, x1=8+80=88, y1=8+40=48, t=round(0.5*8)=4
    assert "BOX 8,8,88,48,4" in out


def test_filled_rect_emits_BAR():
    out = _gen([{"type": "rect", "x": 0, "y": 0, "width": 10, "height": 5, "fill": "#000"}])
    assert "BAR 0,0,80,40" in out


def test_horizontal_line_emits_BAR():
    out = _gen([{"type": "line", "x": 0, "y": 0, "points": [0, 0, 10, 0], "strokeWidth": 0.25}])
    assert out.count("BAR 0,0,80,") == 1


def test_image_skipped_with_warning():
    warnings = []
    out = _gen([{"type": "image", "id": "img1", "x": 0, "y": 0}], warnings)
    assert "TEXT" not in out and "BAR" not in out
    assert any(w["object_id"] == "img1" for w in warnings)


def test_rotation_snapped_with_warning():
    warnings = []
    _gen([{"type": "text", "x": 0, "y": 0, "fontSize": 3, "text": "x", "rotation": 45}], warnings)
    assert any("snapped" in w["message"] for w in warnings)


def test_table_emits_box_and_cells():
    obj = {
        "type": "table", "id": "t1", "x": 0, "y": 0, "width": 40, "height": 20,
        "rows": 2, "cols": 2, "strokeWidth": 0.2, "fontSize": 3,
        "cells": [["A", "B"], ["C", "D"]],
    }
    out = _gen([obj])
    assert out.count("BOX ") == 1
    assert 'TEXT' in out and '"A"' in out and '"D"' in out
```

- [ ] **Step 4: Run the tests**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/backend
python -m pytest tests/test_tspl.py -v
```
Expected: all PASS. If `table_col_edges` import fails, confirm it exists: `grep -n "def table_col_edges" app/services/pdf_renderer.py`.

- [ ] **Step 5: Lint + commit**

```bash
cd /var/www/html/BarcodeLabelGen/backend
ruff check app/services/tspl/ tests/test_tspl.py
cd /var/www/html/BarcodeLabelGen
git add backend/app/services/tspl/ backend/tests/test_tspl.py
git commit -m "feat(tspl): canvas → TSPL generator for TSC/Toshiba (F22)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
Expected: ruff clean, commit made.

---

### Task 2: TSPL export endpoint (`/api/tspl/generate`)

**Files:**
- Create: `backend/app/routes/tspl.py`
- Modify: `backend/app/factory.py` (import + register blueprint, next to `zpl_bp` on line ~100)
- Test: `backend/tests/test_tspl_endpoints.py`

**Interfaces:**
- Consumes: `generate_tspl` (Task 1); `dpmm_for_dpi` from `app.services.zpl.units`; `substitute_dates_in_canvas`; `_safe_filename` from `app.routes.generate`; `templates as tpl_svc`.
- Produces: `tspl_bp` blueprint with `POST /tspl/generate`.

- [ ] **Step 1: Write `backend/app/routes/tspl.py`**

```python
"""HTTP endpoint for TSPL export (single-label / template mode).

Mirrors the ZPL generate endpoint's `mode="template"` branch: resolve the
canvas (live editor or saved template), evaluate {{date+x}} placeholders,
render TSPL, and return it as a downloadable attachment.
"""

from __future__ import annotations

import json
from typing import Any

from flask import Blueprint, Response, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import BaseModel, ValidationError

from app.api_helpers import validation_error_response
from app.db.session import get_session
from app.routes.generate import _safe_filename
from app.services import templates as tpl_svc
from app.services.placeholders import substitute_dates_in_canvas
from app.services.tspl import generate_tspl
from app.services.zpl.units import dpmm_for_dpi

tspl_bp = Blueprint("tspl", __name__)


class TsplGenerateRequest(BaseModel):
    template_id: int | None = None
    canvas_data: dict[str, Any] | None = None
    dpi: int = 203


def _resolve_canvas(payload: TsplGenerateRequest) -> dict[str, Any] | None:
    if payload.canvas_data is not None:
        return payload.canvas_data
    if payload.template_id is None:
        return None
    session = get_session()
    tpl = tpl_svc.get(session, payload.template_id, requesting_user_id=current_user.id)
    return dict(tpl.canvas_data) if tpl.canvas_data else {}


def _resolve_template_name(template_id: int) -> str | None:
    session = get_session()
    try:
        tpl = tpl_svc.get(session, template_id, requesting_user_id=current_user.id)
    except (tpl_svc.TemplateNotFoundError, tpl_svc.TemplateAccessError):
        return None
    return _safe_filename(tpl.name)


@tspl_bp.post("/tspl/generate")
@login_required
def generate_endpoint() -> ResponseReturnValue:
    try:
        payload = TsplGenerateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    try:
        canvas_data = _resolve_canvas(payload)
    except tpl_svc.TemplateNotFoundError:
        return jsonify({"error": "template_not_found"}), 404
    except tpl_svc.TemplateAccessError:
        return jsonify({"error": "forbidden"}), 403
    if canvas_data is None:
        return jsonify({"error": "no_canvas", "detail": "provide canvas_data or template_id"}), 400

    canvas_data = substitute_dates_in_canvas(canvas_data)
    warnings: list[dict[str, Any]] = []
    tspl_text = generate_tspl(canvas_data, dpmm=dpmm_for_dpi(payload.dpi), warnings=warnings)

    name = "labels"
    if payload.template_id is not None:
        name = _resolve_template_name(payload.template_id) or name

    response = Response(tspl_text, mimetype="text/plain; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{name}.txt"'
    response.headers["Cache-Control"] = "no-store"
    if warnings:
        response.headers["X-TSPL-Warnings"] = json.dumps(warnings)
        response.headers["Access-Control-Expose-Headers"] = "X-TSPL-Warnings"
    return response
```

- [ ] **Step 2: Register the blueprint in `backend/app/factory.py`**

Add the import next to the other route imports (near `from app.routes.zpl import zpl_bp`):

```python
from app.routes.tspl import tspl_bp
```

And register it right after the `zpl_bp` registration line:

```python
    app.register_blueprint(zpl_bp, url_prefix="/api")
    app.register_blueprint(tspl_bp, url_prefix="/api")
```

- [ ] **Step 3: Write `backend/tests/test_tspl_endpoints.py`**

```python
"""HTTP-layer tests for the TSPL export endpoint (auth + wiring)."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper

_CANVAS = {
    "stage": {"width_mm": 50, "height_mm": 30, "zpl": {"dpmm": 8}},
    "objects": [{"type": "text", "x": 5, "y": 5, "fontSize": 3, "text": "Hi"}],
}


def _login(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    with app.app_context():
        sess = get_session()
        create_user(sess, email="tspl@example.com", plain_password="password123!", role=Role.EDITOR)
    client.post(
        "/api/auth/login",
        json={"email": "tspl@example.com", "password": "password123!"},
        headers=csrf.headers(),
    )


def test_generate_rejects_unauthenticated(client: FlaskClient, csrf: CsrfHelper) -> None:
    resp = client.post("/api/tspl/generate", json={"canvas_data": _CANVAS}, headers=csrf.headers())
    assert resp.status_code == 401


def test_generate_returns_tspl_attachment(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    resp = client.post(
        "/api/tspl/generate", json={"canvas_data": _CANVAS, "dpi": 203}, headers=csrf.headers()
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/plain"
    assert 'attachment; filename="labels.txt"' in resp.headers["Content-Disposition"]
    body = resp.get_data(as_text=True)
    assert body.startswith("SIZE 50 mm, 30 mm")
    assert body.rstrip().endswith("PRINT 1")


def test_generate_no_canvas_is_400(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    resp = client.post("/api/tspl/generate", json={}, headers=csrf.headers())
    assert resp.status_code == 400


def test_generate_image_sets_warning_header(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    canvas = {
        "stage": {"width_mm": 50, "height_mm": 30, "zpl": {"dpmm": 8}},
        "objects": [{"type": "image", "id": "img1", "x": 0, "y": 0}],
    }
    resp = client.post("/api/tspl/generate", json={"canvas_data": canvas}, headers=csrf.headers())
    assert resp.status_code == 200
    assert "X-TSPL-Warnings" in resp.headers
```

- [ ] **Step 4: Run the tests**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/backend
python -m pytest tests/test_tspl_endpoints.py -v
```
Expected: all PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd /var/www/html/BarcodeLabelGen/backend
ruff check app/routes/tspl.py tests/test_tspl_endpoints.py app/factory.py
cd /var/www/html/BarcodeLabelGen
git add backend/app/routes/tspl.py backend/app/factory.py backend/tests/test_tspl_endpoints.py
git commit -m "feat(tspl): POST /api/tspl/generate export endpoint (F22)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Frontend — TSPL export modal + wiring

**Files:**
- Create: `frontend/src/hooks/useTspl.ts`
- Create: `frontend/src/editor/ExportTsplModal.tsx`
- Modify: `frontend/src/editor/Toolbar.tsx` (add `onExportTspl` prop + button)
- Modify: `frontend/src/pages/EditorPage.tsx` (state + modal wiring)
- Modify: `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pl.json` (tspl.* keys)

**Interfaces:**
- Consumes: `POST /api/tspl/generate` (Task 2), returning TSPL text + `X-TSPL-Warnings` header.
- Produces: `useGenerateTspl()` hook; `ExportTsplModal`; a Toolbar "Export TSPL" action.

- [ ] **Step 1: Write `frontend/src/hooks/useTspl.ts`**

```ts
import { useMutation } from "@tanstack/react-query";
import type { CanvasData } from "../editor/types";
import { readCsrfCookie } from "../lib/csrf";

export type TsplWarning = { object_id: string; row?: number; message: string };

export type TsplGenerateResult = {
  tspl: string;
  warnings: TsplWarning[];
};

/**
 * Generate TSPL from a canvas (single-label mode). Sends the live editor
 * canvas and reads the optional `X-TSPL-Warnings` header (e.g. an image
 * object that can't be emitted, or an approximated font).
 */
export function useGenerateTspl() {
  return useMutation({
    mutationFn: async (input: { canvas_data: CanvasData; dpi: number }): Promise<TsplGenerateResult> => {
      const csrf = readCsrfCookie();
      const response = await fetch("/api/tspl/generate", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        },
        body: JSON.stringify(input),
      });
      if (!response.ok) {
        let detail = "TSPL generation failed";
        try {
          const b = (await response.json()) as { error?: string; detail?: string };
          detail = b.detail ?? b.error ?? detail;
        } catch {
          // non-JSON body — keep generic message
        }
        throw new Error(detail);
      }
      let warnings: TsplWarning[] = [];
      const raw = response.headers.get("X-TSPL-Warnings");
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as unknown;
          if (Array.isArray(parsed)) warnings = parsed as TsplWarning[];
        } catch {
          // corrupt header → no warnings
        }
      }
      const tspl = await response.text();
      return { tspl, warnings };
    },
  });
}
```

- [ ] **Step 2: Write `frontend/src/editor/ExportTsplModal.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { type TsplWarning, useGenerateTspl } from "../hooks/useTspl";
import type { CanvasData } from "./types";

type Props = {
  open: boolean;
  onClose: () => void;
  canvas: CanvasData;
  templateName: string;
};

function safeName(name: string): string {
  return name.replace(/[^A-Za-z0-9._-]+/g, "_") || "labels";
}

export function ExportTsplModal({ open, onClose, canvas, templateName }: Props) {
  const { t } = useTranslation();
  const [dpi, setDpi] = useState(203);
  const generate = useGenerateTspl();
  const [tspl, setTspl] = useState("");
  const [warnings, setWarnings] = useState<TsplWarning[]>([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) return;
    const handle = setTimeout(() => {
      generate.mutate(
        { canvas_data: canvas, dpi },
        { onSuccess: (r) => { setTspl(r.tspl); setWarnings(r.warnings); } },
      );
    }, 300);
    return () => clearTimeout(handle);
    // generate is stable (react-query); intentionally omitted
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, canvas, dpi]);

  const handleCopy = () => {
    void navigator.clipboard.writeText(tspl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const handleDownload = () => {
    const blob = new Blob([tspl], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${safeName(templateName)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Modal open={open} onClose={onClose} title={t("tspl.exportTitle")}>
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-300">{t("tspl.dpi")}</label>
          <Select value={String(dpi)} onChange={(e) => setDpi(Number(e.target.value))}>
            <option value="203">203 dpi</option>
            <option value="300">300 dpi</option>
          </Select>
        </div>
        {warnings.length > 0 && (
          <div className="rounded-md border border-amber-900 bg-amber-950/40 px-3 py-2 text-xs text-amber-300">
            <p className="mb-1 font-medium">{t("tspl.warnings", { count: warnings.length })}</p>
            <ul className="list-disc pl-4">
              {warnings.slice(0, 5).map((w, i) => (
                <li key={i}>{w.message}</li>
              ))}
            </ul>
          </div>
        )}
        <textarea
          readOnly
          value={tspl}
          className="h-64 w-full rounded border border-slate-700 bg-slate-900 p-2 font-mono text-xs text-slate-200"
        />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={handleCopy}>
            {copied ? t("common.copied") : t("common.copy")}
          </Button>
          <Button onClick={handleDownload}>{t("tspl.download")}</Button>
        </div>
      </div>
    </Modal>
  );
}
```

Note: if `Modal` does not accept a `title` prop or `Select` has a different API, match the exact props used by `ExportZplModal.tsx` (read it first) — reuse whatever that file uses.

- [ ] **Step 3: Wire into `Toolbar.tsx`**

Add to the `Props` type (near `onExportZpl: () => void;`):

```tsx
  onExportTspl: () => void;
```

Add to the destructured params (near `onExportZpl,`):

```tsx
  onExportTspl,
```

Add a button right after the existing Export ZPL button (near the `onExportZpl` button around line 142):

```tsx
        <Button variant="ghost" onClick={onExportTspl} title={t("tspl.exportTooltip")}>
          {t("tspl.export")}
        </Button>
```

- [ ] **Step 4: Wire into `EditorPage.tsx`**

Add the import (near `import { ExportZplModal } ...`):

```tsx
import { ExportTsplModal } from "../editor/ExportTsplModal";
```

Add state (near `const [showExportZpl, setShowExportZpl] = useState(false);`):

```tsx
  const [showExportTspl, setShowExportTspl] = useState(false);
```

Pass the handler to `<Toolbar>` (near `onExportZpl={() => setShowExportZpl(true)}`):

```tsx
        onExportTspl={() => setShowExportTspl(true)}
```

Render the modal next to `<ExportZplModal ...>` (inside the `{canvas && (` block, mirroring ExportZplModal's placement):

```tsx
          <ExportTsplModal
            open={showExportTspl}
            onClose={() => setShowExportTspl(false)}
            canvas={canvas}
            templateName={template.data.name}
          />
```

- [ ] **Step 5: Add i18n keys**

In `frontend/src/i18n/locales/en.json`, add a `tspl` block (mirror the existing `zpl` block's location):

```json
  "tspl": {
    "export": "Export TSPL",
    "exportTooltip": "Export this label as TSPL for TSC / Toshiba printers",
    "exportTitle": "Export TSPL",
    "dpi": "Density",
    "download": "Download .txt",
    "warnings": "{{count}} warning(s)"
  }
```

In `frontend/src/i18n/locales/pl.json`:

```json
  "tspl": {
    "export": "Eksportuj TSPL",
    "exportTooltip": "Eksportuj etykietę jako TSPL (drukarki TSC / Toshiba)",
    "exportTitle": "Eksport TSPL",
    "dpi": "Gęstość",
    "download": "Pobierz .txt",
    "warnings": "Ostrzeżenia: {{count}}"
  }
```

If `common.copy`/`common.copied` don't already exist (ExportZplModal uses them — verify), reuse the existing keys; do not duplicate.

- [ ] **Step 6: Typecheck + lint + commit**

```bash
cd /var/www/html/BarcodeLabelGen/frontend
npm run typecheck && npm run lint
cd /var/www/html/BarcodeLabelGen
git add frontend/src/hooks/useTspl.ts frontend/src/editor/ExportTsplModal.tsx frontend/src/editor/Toolbar.tsx frontend/src/pages/EditorPage.tsx frontend/src/i18n/locales/en.json frontend/src/i18n/locales/pl.json
git commit -m "feat(tspl): editor Export TSPL modal + wiring (F22)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
Expected: typecheck + lint clean.

---

### Task 4: Docs, version bump, release v0.20.0

**Files:**
- Modify: `docs/PROJECT.md` (F22 row), `CHANGELOG.md`, `frontend/package.json`, `backend/pyproject.toml`

**Interfaces:**
- Consumes: the shipped generator + endpoint + UI (Tasks 1–3).
- Produces: tag `v0.20.0`, notes-only GitHub release.

- [ ] **Step 1: Mark F22 done in PROJECT.md**

In `docs/PROJECT.md`, find the `| F22 |` row and append to its description (before the trailing `| P2 |`): ` — **zrealizowane w v0.20.0** (eksport TSPL z edytora; druk przez agenta i TPCL poza zakresem)`.

- [ ] **Step 2: Bump versions**

```bash
cd /var/www/html/BarcodeLabelGen
sed -i 's/"version": "0.19.1"/"version": "0.20.0"/' frontend/package.json
sed -i '0,/^version = "0.19.1"/s//version = "0.20.0"/' backend/pyproject.toml
grep '"version"' frontend/package.json; grep -m1 '^version' backend/pyproject.toml
```
Expected: both `0.20.0`.

- [ ] **Step 3: Add the CHANGELOG section**

In `CHANGELOG.md`, insert directly above the most recent version section (`## [0.19.1] — 2026-07-05`):

```markdown
## [0.20.0] — 2026-07-05

### Added
- **TSPL export for TSC / desktop Toshiba printers (F22).** A new "Export
  TSPL" action in the editor renders the label as TSPL/TSPL2 (SIZE/GAP/
  DIRECTION/CLS … PRINT) — text, barcodes (Code 128, GS1-128, EAN-13, QR),
  rectangles, lines and tables; images are skipped with a warning. New
  `app/services/tspl/` generator (reusing the ZPL mm→dots math) and
  `POST /api/tspl/generate` endpoint mirroring ZPL's single-label export.
  Font sizing and GAP are documented approximations (TSPL bitmap fonts vs
  the editor's TrueType); actual printing is verified on a physical TSC
  printer. TPCL, agent-printing and batch TSPL remain out of scope.
```

Then update the reference links — replace:
```markdown
[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.19.1...HEAD
[0.19.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.19.1
```
with:
```markdown
[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.20.0...HEAD
[0.20.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.20.0
[0.19.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.19.1
```

- [ ] **Step 4: Commit, tag, push**

```bash
cd /var/www/html/BarcodeLabelGen
git add docs/PROJECT.md CHANGELOG.md frontend/package.json backend/pyproject.toml
git commit -m "chore(release): v0.20.0 — TSPL export (F22)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git tag -a v0.20.0 -m "v0.20.0 — TSPL export (F22)"
git push origin main && git push origin v0.20.0
```

- [ ] **Step 5: Create the GitHub release (notes only)**

```bash
cd /var/www/html/BarcodeLabelGen
gh release create v0.20.0 \
  --title "v0.20.0 — TSPL export (F22)" \
  --notes "$(awk '/^## \[0.20.0\]/{f=1;next} /^## \[0.19.1\]/{f=0} f' CHANGELOG.md)"
gh release view v0.20.0 --json tagName --jq .tagName
```
Expected: release URL printed; tag `v0.20.0`.

---

## Notes for the implementer

- **Rebuild the running app to verify live** is optional for the backend gate (pytest covers it); the editor UI change (Task 3) is verified on the live instance separately by the controller (headless Chromium with an injected session), not in this task.
- **Do not modify `app/services/zpl/`.** TSPL imports from `zpl.units` only.
- Before writing `ExportTsplModal`, read `frontend/src/editor/ExportZplModal.tsx` to match the exact `Modal`/`Select`/`Button` prop APIs and the `common.copy`/`common.copied` i18n keys — reuse, don't reinvent.
- The generator is the verifiable core (Tasks 1–2, pytest). Tasks 3–4 must not regress the backend gate.
