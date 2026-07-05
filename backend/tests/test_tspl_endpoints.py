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


def test_generate_returns_tspl_attachment(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
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


def test_generate_image_sets_warning_header(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    canvas = {
        "stage": {"width_mm": 50, "height_mm": 30, "zpl": {"dpmm": 8}},
        "objects": [{"type": "image", "id": "img1", "x": 0, "y": 0}],
    }
    resp = client.post("/api/tspl/generate", json={"canvas_data": canvas}, headers=csrf.headers())
    assert resp.status_code == 200
    assert "X-TSPL-Warnings" in resp.headers
