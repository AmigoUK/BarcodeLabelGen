"""HTTP-layer tests for the ZPL parse/generate endpoints (auth + wiring)."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper

_SAMPLE = "^XA\n^FO80,80^A@N,28,28,E:ARI001.TTF^FD{NAZWA}^FS\n^PQ{NoLabel},0,1,Y\n^XZ"


def _login(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    with app.app_context():
        sess = get_session()
        create_user(sess, email="zpl@example.com", plain_password="password123!", role=Role.EDITOR)
    client.post(
        "/api/auth/login",
        json={"email": "zpl@example.com", "password": "password123!"},
        headers=csrf.headers(),
    )


def test_parse_rejects_unauthenticated(client: FlaskClient, csrf: CsrfHelper) -> None:
    # With a CSRF token but no session, the endpoint must reject (401).
    assert (
        client.post("/api/zpl/parse", json={"zpl": _SAMPLE}, headers=csrf.headers()).status_code
        == 401
    )


def test_parse_returns_canvas(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    resp = client.post(
        "/api/zpl/parse", json={"zpl": _SAMPLE, "dpi": 203}, headers=csrf.headers()
    )
    assert resp.status_code == 200
    body = resp.get_json()
    objs = body["canvas_data"]["objects"]
    assert objs[0]["type"] == "text"
    assert objs[0]["text"] == "{NAZWA}"
    assert body["canvas_data"]["stage"]["zpl"]["pq"] == "{NoLabel},0,1,Y"


def test_generate_template_returns_zpl_text(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    parsed = client.post(
        "/api/zpl/parse", json={"zpl": _SAMPLE, "dpi": 203}, headers=csrf.headers()
    ).get_json()
    resp = client.post(
        "/api/zpl/generate",
        json={"canvas_data": parsed["canvas_data"], "dpi": 203, "mode": "template"},
        headers=csrf.headers(),
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/plain"
    text = resp.get_data(as_text=True)
    assert "^A@N,28,28,E:ARI001.TTF" in text
    assert "^FD{NAZWA}^FS" in text
    assert "^PQ{NoLabel},0,1,Y" in text


def test_generate_batch_requires_dataset(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    resp = client.post(
        "/api/zpl/generate",
        json={"template_id": 999, "mode": "batch", "dpi": 203},
        headers=csrf.headers(),
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "batch_requires_template_and_dataset"
