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
    assert '"Hi"' in out


def test_text_with_width_emits_BLOCK():
    out = _gen([{"type": "text", "x": 0, "y": 0, "width": 20, "fontSize": 3, "text": "wrap"}])
    assert "BLOCK 0,0,160," in out


def test_text_escapes_quote():
    out = _gen([{"type": "text", "x": 0, "y": 0, "fontSize": 3, "text": 'a"b'}])
    assert 'a\\[22]b' in out


def test_barcode_code128():
    out = _gen(
        [{"type": "barcode", "x": 2, "y": 2, "barcodeType": "code128", "height": 10, "data": "ABC"}]
    )
    assert 'BARCODE 16,16,"128",80,1,0,2,2,"ABC"' in out


def test_barcode_ean13():
    out = _gen(
        [{"type": "barcode", "x": 0, "y": 0, "barcodeType": "ean13", "height": 10, "data": "590"}]
    )
    assert '"EAN13"' in out


def test_barcode_gs1_128():
    out = _gen(
        [{"type": "barcode", "x": 0, "y": 0, "barcodeType": "gs1_128", "height": 10, "data": "X"}]
    )
    assert '"EAN128"' in out


def test_barcode_unknown_warns_and_falls_back():
    warnings = []
    out = _gen(
        [{"type": "barcode", "x": 0, "y": 0, "barcodeType": "pdf417", "height": 10, "data": "X"}],
        warnings,
    )
    assert '"128"' in out
    assert any("not mapped" in w["message"] for w in warnings)


def test_qr_emits_QRCODE():
    out = _gen(
        [{"type": "barcode", "x": 1, "y": 1, "barcodeType": "qr", "height": 12, "data": "url"}]
    )
    assert out.count("QRCODE 8,8,M,") == 1
    assert '"url"' in out


def test_rect_outline_emits_BOX():
    out = _gen(
        [
            {
                "type": "rect",
                "x": 1,
                "y": 1,
                "width": 10,
                "height": 5,
                "stroke": "#000",
                "strokeWidth": 0.5,
            }
        ]
    )
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
    assert 'BLOCK' in out and '"A"' in out and '"D"' in out
