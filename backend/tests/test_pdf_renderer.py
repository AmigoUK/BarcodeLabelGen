from __future__ import annotations

from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.label_format import FormatKind, LabelFormat
from app.services.pdf_renderer import (
    PdfRenderError,
    render_template_pdf,
)
from app.services.users import create_user
from tests.conftest import CsrfHelper

PDF_MAGIC = b"%PDF-"


# --- service-layer unit tests ---


def _empty_canvas() -> dict[str, Any]:
    return {"version": 1, "stage": {"width_mm": 105, "height_mm": 148}, "objects": []}


def test_render_empty_canvas_returns_valid_pdf() -> None:
    pdf = render_template_pdf(_empty_canvas(), width_mm=105, height_mm=148)
    assert pdf.startswith(PDF_MAGIC)
    assert b"%%EOF" in pdf[-1024:]


def test_render_rejects_non_dict() -> None:
    with pytest.raises(PdfRenderError):
        render_template_pdf("not a dict", width_mm=10, height_mm=10)  # type: ignore[arg-type]


def test_render_with_text_object() -> None:
    canvas = {
        "version": 1,
        "stage": {"width_mm": 105, "height_mm": 148},
        "objects": [
            {
                "id": "t1",
                "type": "text",
                "x": 10,
                "y": 10,
                "text": "Hello PDF",
                "fontSize": 4,
                "fontFamily": "Helvetica",
                "fill": "#000000",
            }
        ],
    }
    pdf = render_template_pdf(canvas, width_mm=105, height_mm=148)
    assert pdf.startswith(PDF_MAGIC)
    # ReportLab flate-compresses content streams, so we can't grep for the
    # literal text. Instead verify the PDF is well-formed and bigger than
    # the empty-canvas baseline (~700 B).
    assert len(pdf) > 800
    assert b"%%EOF" in pdf[-1024:]


def test_render_with_rect_and_line() -> None:
    canvas = {
        "version": 1,
        "stage": {"width_mm": 105, "height_mm": 148},
        "objects": [
            {
                "id": "r1",
                "type": "rect",
                "x": 5,
                "y": 5,
                "width": 50,
                "height": 30,
                "fill": "#cccccc",
                "stroke": "#000000",
                "strokeWidth": 0.5,
            },
            {
                "id": "l1",
                "type": "line",
                "x": 5,
                "y": 50,
                "points": [0, 0, 80, 0],
                "stroke": "#0066cc",
                "strokeWidth": 0.4,
            },
        ],
    }
    pdf = render_template_pdf(canvas, width_mm=105, height_mm=148)
    assert pdf.startswith(PDF_MAGIC)


def test_render_with_barcode() -> None:
    canvas = {
        "version": 1,
        "stage": {"width_mm": 105, "height_mm": 148},
        "objects": [
            {
                "id": "b1",
                "type": "barcode",
                "barcodeType": "ean13",
                "data": "590123456789",
                "x": 10,
                "y": 10,
                "width": 50,
                "height": 20,
            }
        ],
    }
    pdf = render_template_pdf(canvas, width_mm=105, height_mm=148)
    assert pdf.startswith(PDF_MAGIC)
    # PDF should contain image XObjects for the barcode bitmap
    assert b"/Image" in pdf


def test_invalid_barcode_data_does_not_kill_other_objects() -> None:
    canvas = {
        "version": 1,
        "stage": {"width_mm": 105, "height_mm": 148},
        "objects": [
            {
                "id": "b_bad",
                "type": "barcode",
                "barcodeType": "ean13",
                "data": "ABCD",  # letters: render fails
                "x": 5,
                "y": 5,
                "width": 50,
                "height": 20,
            },
            {
                "id": "t1",
                "type": "text",
                "x": 5,
                "y": 50,
                "text": "Still here",
                "fontSize": 4,
                "fontFamily": "Helvetica",
                "fill": "#000000",
            },
        ],
    }
    pdf = render_template_pdf(canvas, width_mm=105, height_mm=148)
    # Render survives the bad barcode and emits a valid PDF
    assert pdf.startswith(PDF_MAGIC)
    assert len(pdf) > 800


def test_text_block_wraps_long_text_into_multiple_lines() -> None:
    long_text = (
        "Producent ABC oferuje wysokiej jakosci wyroby etykietowe "
        "dostosowane do potrzeb przemyslu i handlu detalicznego."
    )
    canvas = {
        "version": 1,
        "stage": {"width_mm": 80, "height_mm": 80},
        "objects": [
            {
                "id": "tb",
                "type": "text",
                "x": 5,
                "y": 5,
                "width": 50,
                "height": 40,
                "text": long_text,
                "fontSize": 4,
                "fontFamily": "Helvetica",
                "fill": "#000",
            }
        ],
    }
    pdf = render_template_pdf(canvas, width_mm=80, height_mm=80)
    assert pdf.startswith(PDF_MAGIC)

    # Read back glyph y-positions; multiple distinct rows means wrapping
    # actually happened.
    import io as _io

    import pdfplumber

    with pdfplumber.open(_io.BytesIO(pdf)) as doc:
        page = doc.pages[0]
        rounded = sorted({round(c["top"]) for c in page.chars})
    assert len(rounded) >= 3, f"expected ≥3 wrapped lines, got y-rows {rounded}"


def test_text_block_autofit_no_warning_when_it_fits() -> None:
    long_text = (
        "Bardzo dlugi opis ktory na pewno nie zmiesci sie "
        "w pudelku przy maksymalnej wielkosci czcionki."
    )
    canvas = {
        "version": 1,
        "stage": {"width_mm": 60, "height_mm": 30},
        "objects": [
            {
                "id": "auto",
                "type": "text",
                "x": 2,
                "y": 2,
                "width": 50,
                "height": 20,
                "text": long_text,
                "fontSize": 8,
                "fontFamily": "Helvetica",
                "fill": "#000",
                "autoFit": True,
                "minFontSize": 2.0,
                "maxFontSize": 8.0,
            }
        ],
    }
    warnings: list[dict[str, Any]] = []
    pdf = render_template_pdf(canvas, width_mm=60, height_mm=30, warnings=warnings)
    assert pdf.startswith(PDF_MAGIC)
    # AutoFit should find a size that fits — no warning expected.
    assert warnings == []


def test_text_block_warns_when_overflow_at_min_size() -> None:
    huge_text = "X" * 400  # nothing fits in a 10×5 mm box, even at 2 mm
    canvas = {
        "version": 1,
        "stage": {"width_mm": 30, "height_mm": 30},
        "objects": [
            {
                "id": "overflow",
                "type": "text",
                "x": 1,
                "y": 1,
                "width": 10,
                "height": 5,
                "text": huge_text,
                "fontSize": 4,
                "fontFamily": "Helvetica",
                "fill": "#000",
                "autoFit": True,
                "minFontSize": 2.0,
                "maxFontSize": 6.0,
            }
        ],
    }
    warnings: list[dict[str, Any]] = []
    pdf = render_template_pdf(canvas, width_mm=30, height_mm=30, warnings=warnings)
    assert pdf.startswith(PDF_MAGIC)
    assert len(warnings) == 1
    assert warnings[0]["object_id"] == "overflow"
    assert "didn't fit" in warnings[0]["message"]


def test_legacy_text_object_unchanged_without_block_fields() -> None:
    """Single-line TextObject (no width+height) keeps legacy behaviour
    and never produces a warning, even with very long text."""
    canvas = {
        "version": 1,
        "stage": {"width_mm": 100, "height_mm": 50},
        "objects": [
            {
                "id": "leg",
                "type": "text",
                "x": 5,
                "y": 10,
                "text": "Single line that may run beyond the page; legacy mode does no wrapping",
                "fontSize": 4,
                "fontFamily": "Helvetica",
                "fill": "#000",
            }
        ],
    }
    warnings: list[dict[str, Any]] = []
    pdf = render_template_pdf(canvas, width_mm=100, height_mm=50, warnings=warnings)
    assert pdf.startswith(PDF_MAGIC)
    assert warnings == []


def test_unknown_object_type_skipped() -> None:
    canvas = {
        "version": 1,
        "stage": {"width_mm": 105, "height_mm": 148},
        "objects": [
            {"id": "x", "type": "unicorn", "x": 1, "y": 1},
            {
                "id": "t",
                "type": "text",
                "x": 1,
                "y": 1,
                "text": "ok",
                "fontSize": 3,
                "fontFamily": "Helvetica",
                "fill": "#000",
            },
        ],
    }
    pdf = render_template_pdf(canvas, width_mm=50, height_mm=50)
    assert pdf.startswith(PDF_MAGIC)
    # PDF rendered cleanly; the "unicorn" object was ignored without error
    assert b"%%EOF" in pdf[-1024:]


# --- HTTP endpoint integration ---


def _seed_format_and_login(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> int:
    with app.app_context():
        sess = get_session()
        fmt = LabelFormat(name="A6", width_mm=105, height_mm=148, kind=FormatKind.A_PAPER)
        sess.add(fmt)
        sess.commit()
        fmt_id = fmt.id
        create_user(sess, email="u@example.com", plain_password="password123!")
    client.post(
        "/api/auth/login",
        json={"email": "u@example.com", "password": "password123!"},
        headers=csrf.headers(),
    )
    return fmt_id


def test_generate_endpoint_returns_pdf(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    created = client.post(
        "/api/templates",
        json={
            "name": "Gen test",
            "format_id": fmt_id,
            "canvas_data": {
                "version": 1,
                "stage": {"width_mm": 105, "height_mm": 148},
                "objects": [
                    {
                        "id": "t1",
                        "type": "text",
                        "x": 10,
                        "y": 10,
                        "text": "Hello",
                        "fontSize": 4,
                        "fontFamily": "Helvetica",
                        "fill": "#000000",
                    }
                ],
            },
        },
        headers=csrf.headers(),
    )
    tid = created.get_json()["id"]

    response = client.post("/api/generate", json={"template_id": tid}, headers=csrf.headers())
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(PDF_MAGIC)
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "Gen_test.pdf" in response.headers["Content-Disposition"]


def test_generate_unknown_template_returns_404(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _seed_format_and_login(app, client, csrf)
    response = client.post("/api/generate", json={"template_id": 99999}, headers=csrf.headers())
    assert response.status_code == 404


def test_generate_requires_auth(client: FlaskClient) -> None:
    response = client.post("/api/generate", json={"template_id": 1}, headers={"X-CSRF-Token": "x"})
    # No CSRF cookie set yet → CSRF check fires first (403). Auth would
    # be 401 if the cookie were present. Either way, mutating endpoints
    # are protected.
    assert response.status_code in (401, 403)
