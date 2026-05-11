from __future__ import annotations

import io
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from PIL import Image

from app.db.session import get_session
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper


@pytest.fixture(autouse=True)
def _isolate_assets_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSETS_DIR", str(tmp_path / "assets"))


def _login(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, *, email: str = "u@example.com"
) -> None:
    with app.app_context():
        create_user(get_session(), email=email, plain_password="password123!", role=Role.EDITOR)
    client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123!"},
        headers=csrf.headers(),
    )


def _png_bytes(size: tuple[int, int] = (10, 10)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, (255, 0, 0, 255)).save(buf, format="PNG")
    return buf.getvalue()


def test_upload_png_returns_metadata(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    response = client.post(
        "/api/assets/images",
        data={"file": (io.BytesIO(_png_bytes((40, 30))), "logo.png")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["original_filename"] == "logo.png"
    assert body["mime_type"] == "image/png"
    assert body["width_px"] == 40
    assert body["height_px"] == 30


def test_upload_oversize_rejected(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    big = b"x" * (5 * 1024 * 1024 + 1)
    response = client.post(
        "/api/assets/images",
        data={"file": (io.BytesIO(big), "huge.png")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "upload_rejected"


def test_upload_unknown_mime_rejected(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    response = client.post(
        "/api/assets/images",
        data={"file": (io.BytesIO(b"garbage"), "evil.exe")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 400


def test_serve_image_round_trip(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/assets/images",
        data={"file": (io.BytesIO(_png_bytes()), "x.png")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    asset_id = upload.get_json()["id"]

    response = client.get(f"/api/assets/images/{asset_id}")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert len(response.data) > 0


def test_other_user_cannot_serve_image(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf, email="alice@example.com")
    upload = client.post(
        "/api/assets/images",
        data={"file": (io.BytesIO(_png_bytes()), "alice.png")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    asset_id = upload.get_json()["id"]

    client.post("/api/auth/logout", headers=csrf.headers())
    _login(app, client, csrf, email="bob@example.com")
    response = client.get(f"/api/assets/images/{asset_id}")
    assert response.status_code == 403
