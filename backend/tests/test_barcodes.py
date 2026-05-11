from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.services.barcodes import (
    BarcodeRenderError,
    BarcodeType,
    normalize_data,
    render_png,
)
from app.services.users import create_user
from tests.conftest import CsrfHelper

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# --- unit: service layer ---


def test_normalize_strips_separators_for_numeric_types() -> None:
    assert normalize_data(BarcodeType.EAN13, "590-1234-56789-3") == "5901234567893"
    assert normalize_data(BarcodeType.GTIN, " 09501101530003 ") == "09501101530003"


def test_normalize_keeps_code128_payload_intact() -> None:
    assert normalize_data(BarcodeType.CODE128, "ABC-123_xyz") == "ABC-123_xyz"


def test_render_ean13_valid_12_digit_auto_checksum() -> None:
    png = render_png(BarcodeType.EAN13, "590123456789")
    assert png.startswith(PNG_MAGIC)


def test_render_ean13_valid_with_checksum() -> None:
    png = render_png(BarcodeType.EAN13, "5901234567893")
    assert png.startswith(PNG_MAGIC)


def test_render_ean13_rejects_letters() -> None:
    with pytest.raises(BarcodeRenderError):
        render_png(BarcodeType.EAN13, "59012345ABCD")


def test_render_ean13_rejects_wrong_length() -> None:
    with pytest.raises(BarcodeRenderError):
        render_png(BarcodeType.EAN13, "12345")


def test_render_ean13_silently_corrects_bad_check_digit() -> None:
    # python-barcode treats a wrong 13th digit as a user typo and recomputes
    # it. That's the desired behaviour — the printed barcode is always valid.
    # We just want to confirm the render still succeeds.
    png = render_png(BarcodeType.EAN13, "5901234567890")
    assert png.startswith(PNG_MAGIC)


def test_render_code128_accepts_alphanumeric() -> None:
    png = render_png(BarcodeType.CODE128, "ORDER-12345-A")
    assert png.startswith(PNG_MAGIC)


def test_render_gtin_valid_13_digits() -> None:
    png = render_png(BarcodeType.GTIN, "9501101530003")
    assert png.startswith(PNG_MAGIC)


def test_render_gs1_128_valid() -> None:
    # GS1 application identifier (01) = GTIN, valid 14-digit payload
    png = render_png(BarcodeType.GS1_128, "(01)09501101530003")
    assert png.startswith(PNG_MAGIC)


def test_render_qr_valid() -> None:
    png = render_png(BarcodeType.QR, "https://example.com/product/42")
    assert png.startswith(PNG_MAGIC)


def test_render_qr_rejects_empty() -> None:
    with pytest.raises(BarcodeRenderError):
        render_png(BarcodeType.QR, "")


def test_render_qr_rejects_oversize() -> None:
    with pytest.raises(BarcodeRenderError):
        render_png(BarcodeType.QR, "x" * 5000)


# --- integration: HTTP endpoint ---


def _login(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    with app.app_context():
        create_user(get_session(), email="u@example.com", plain_password="password123!")
    client.post(
        "/api/auth/login",
        json={"email": "u@example.com", "password": "password123!"},
        headers=csrf.headers(),
    )


def test_preview_requires_auth(client: FlaskClient) -> None:
    response = client.get("/api/barcodes/preview?type=ean13&data=590123456789")
    assert response.status_code == 401


def test_preview_returns_png(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    response = client.get("/api/barcodes/preview?type=ean13&data=590123456789")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(PNG_MAGIC)


def test_preview_unsupported_type_returns_400(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    response = client.get("/api/barcodes/preview?type=widget&data=x")
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "unsupported_type"
    assert "ean13" in body["supported"]


def test_preview_invalid_data_returns_400(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    response = client.get("/api/barcodes/preview?type=ean13&data=NOPE")
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_barcode_data"


def test_preview_sends_cache_header(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    response = client.get("/api/barcodes/preview?type=qr&data=hello")
    assert response.status_code == 200
    assert "max-age" in response.headers.get("Cache-Control", "")
