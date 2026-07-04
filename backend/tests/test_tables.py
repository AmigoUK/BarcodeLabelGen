"""Tables (F7): substitution, PDF rendering, ZPL emission."""

from __future__ import annotations

from datetime import date

import pdfplumber

from app.services.batch_render import render_batch_pdf, substitute_object
from app.services.pdf_renderer import render_template_pdf, table_col_edges
from app.services.placeholders import substitute_dates_in_canvas
from app.services.zpl import generate_zpl

TODAY = date(2026, 7, 4)


def _table(**overrides) -> dict:
    base = {
        "id": "tbl1",
        "type": "table",
        "x": 5,
        "y": 5,
        "width": 60,
        "height": 24,
        "rows": 3,
        "cols": 2,
        "cells": [
            ["Cecha", "Wartość"],
            ["Waga", "{{waga}} g"],
            ["Partia", "{{partia}}"],
        ],
        "headerRow": True,
        "fontSize": 3,
        "fontFamily": "Helvetica",
        "fill": "#0f172a",
        "stroke": "#0f172a",
        "strokeWidth": 0.3,
    }
    base.update(overrides)
    return base


def _canvas(obj: dict) -> dict:
    return {"version": 1, "stage": {"width_mm": 80, "height_mm": 50}, "objects": [obj]}


# --- substitution ------------------------------------------------------------


def test_substitute_object_fills_table_cells() -> None:
    src = _table()
    out = substitute_object(src, {"waga": "250", "partia": "L-77"})
    assert out["cells"][1][1] == "250 g"
    assert out["cells"][2][1] == "L-77"
    # source untouched (fresh 2D copy)
    assert src["cells"][1][1] == "{{waga}} g"


def test_dates_substituted_in_table_cells() -> None:
    obj = _table(cells=[["Data", "{{date+7d}}"]], rows=1, cols=2)
    out = substitute_dates_in_canvas(_canvas(obj), today=TODAY)
    assert out["objects"][0]["cells"][0][1] == "11.07.2026"


# --- geometry helpers --------------------------------------------------------


def test_col_edges_equal_and_custom() -> None:
    assert table_col_edges({"cols": 3, "width": 60}) == [0.0, 20.0, 40.0, 60.0]
    assert table_col_edges({"cols": 2, "width": 60, "colWidths": [20, 40]}) == [0.0, 20.0, 60.0]
    # bad colWidths (wrong length) → equal fallback
    assert table_col_edges({"cols": 2, "width": 60, "colWidths": [10]}) == [0.0, 30.0, 60.0]


# --- PDF ---------------------------------------------------------------------


def test_pdf_renders_table_text() -> None:
    pdf = render_template_pdf(_canvas(_table()), width_mm=80, height_mm=50)
    assert pdf.startswith(b"%PDF-")
    import io

    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        text = doc.pages[0].extract_text()
    assert "Cecha" in text and "Waga" in text and "{{waga}} g" in text


def test_pdf_batch_substitutes_table() -> None:
    pdf = render_batch_pdf(
        _canvas(_table()), [{"waga": "250", "partia": "L-1"}], width_mm=80, height_mm=50
    )
    import io

    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        text = doc.pages[0].extract_text()
    assert "250 g" in text and "L-1" in text


def test_pdf_table_overflow_warns() -> None:
    warnings: list[dict] = []
    obj = _table(
        cells=[["bardzo bardzo bardzo długi tekst który się nie zmieści nigdzie", "x"]],
        rows=1,
        cols=2,
        height=4,
        fontSize=3,
    )
    render_template_pdf(_canvas(obj), width_mm=80, height_mm=50, warnings=warnings)
    assert any("truncated" in w["message"] for w in warnings)


# --- ZPL ---------------------------------------------------------------------


def test_zpl_emits_grid_and_cells() -> None:
    warnings: list[dict] = []
    zpl = generate_zpl(_canvas(_table()), dpmm=8, warnings=warnings)
    # outer box + 1 vertical + 2 horizontal separators = 4 ^GB
    assert zpl.count("^GB") == 4
    assert "^FDCecha^FS" in zpl
    assert "^FD{{waga}} g^FS" in zpl
    assert warnings == []


def test_zpl_table_rotation_warns() -> None:
    warnings: list[dict] = []
    zpl = generate_zpl(_canvas(_table(rotation=45)), dpmm=8, warnings=warnings)
    assert "^GB" in zpl  # emitted anyway
    assert any("rotation" in w["message"] for w in warnings)
