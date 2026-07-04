from __future__ import annotations

from app.services.batch_render import (
    render_batch_pdf,
    substitute_object,
    substitute_string,
)

PDF_MAGIC = b"%PDF-"


def test_substitute_string_replaces_known_placeholders() -> None:
    assert substitute_string("Hello {{name}}", {"name": "Alice"}) == "Hello Alice"


def test_substitute_string_strips_whitespace_inside_braces() -> None:
    assert substitute_string("{{ name }}", {"name": "Bob"}) == "Bob"


def test_substitute_string_replaces_missing_with_empty() -> None:
    assert substitute_string("Hi {{name}}!", {}) == "Hi !"


def test_substitute_string_handles_multiple_placeholders() -> None:
    assert substitute_string("{{a}}-{{b}}", {"a": "X", "b": "Y"}) == "X-Y"


def test_substitute_string_plain_date_prefers_row_column() -> None:
    assert substitute_string("{{date}}", {"date": "row-val"}) == "row-val"


def test_substitute_string_offset_date_ignores_row_column() -> None:
    out = substitute_string("{{date+1d}}", {"date+1d": "row-val", "date": "x"})
    assert out != "row-val"
    assert "." in out  # DD.MM.YYYY default format


def test_substitute_string_plain_date_computed_without_column() -> None:
    out = substitute_string("{{date}}", {})
    assert len(out) == 10 and out[2] == "." and out[5] == "."


def test_substitute_string_invalid_date_syntax_falls_through() -> None:
    assert substitute_string("{{date+xyz}}", {}) == ""
    assert substitute_string("{{date+xyz}}", {"date+xyz": "v"}) == "v"


def test_substitute_object_only_touches_text_and_data() -> None:
    obj = {"type": "text", "text": "{{name}}", "x": 1, "y": 2}
    result = substitute_object(obj, {"name": "Z"})
    assert result["text"] == "Z"
    assert result["x"] == 1
    # Original is not mutated
    assert obj["text"] == "{{name}}"


def test_substitute_object_replaces_barcode_data() -> None:
    obj = {"type": "barcode", "barcodeType": "ean13", "data": "{{ean}}"}
    result = substitute_object(obj, {"ean": "590123456789"})
    assert result["data"] == "590123456789"


def test_substitute_object_leaves_rect_alone() -> None:
    obj = {"type": "rect", "x": 0, "y": 0, "width": 10, "height": 10}
    assert substitute_object(obj, {"x": "9999"}) == obj


def test_render_batch_pdf_produces_one_page_per_row() -> None:
    canvas = {
        "version": 1,
        "stage": {"width_mm": 50, "height_mm": 30},
        "objects": [
            {
                "id": "t1",
                "type": "text",
                "x": 5,
                "y": 5,
                "text": "SKU: {{sku}}",
                "fontSize": 4,
                "fontFamily": "Helvetica",
                "fill": "#000",
            }
        ],
    }
    rows = [{"sku": "A001"}, {"sku": "A002"}, {"sku": "A003"}]
    pdf = render_batch_pdf(canvas, rows, width_mm=50, height_mm=30)
    assert pdf.startswith(PDF_MAGIC)
    # Each row → one page; three /Page entries plus the /Pages catalog
    assert pdf.count(b"/Page\n") >= 3 or pdf.count(b"/Type /Page") >= 3


def test_render_batch_pdf_reports_progress() -> None:
    canvas = {"version": 1, "stage": {"width_mm": 20, "height_mm": 20}, "objects": []}
    calls: list[tuple[int, int]] = []
    rows = [{"x": "1"}, {"x": "2"}]
    render_batch_pdf(
        canvas,
        rows,
        width_mm=20,
        height_mm=20,
        on_progress=lambda done, total: calls.append((done, total)),
    )
    assert calls == [(1, 2), (2, 2)]


def test_render_batch_pdf_empty_rows_still_valid() -> None:
    canvas = {"version": 1, "stage": {"width_mm": 20, "height_mm": 20}, "objects": []}
    pdf = render_batch_pdf(canvas, [], width_mm=20, height_mm=20)
    assert pdf.startswith(PDF_MAGIC)
