"""HTTP tests for the captures inbox (agent upload + session review)."""

from __future__ import annotations

import base64

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper

_ZPL = "^XA^FO40,40^FDcaptured^FS^XZ"


def _setup(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> tuple[int, str]:
    with app.app_context():
        sess = get_session()
        create_user(sess, email="cap@example.com", plain_password="password123!", role=Role.EDITOR)
    client.post(
        "/api/auth/login",
        json={"email": "cap@example.com", "password": "password123!"},
        headers=csrf.headers(),
    )
    body = client.post("/api/devices", json={"name": "Biuro"}, headers=csrf.headers()).get_json()
    return body["device"]["id"], body["token"]


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_upload_requires_token(client: FlaskClient) -> None:
    resp = client.post("/api/agent/captures", json={"zpl_b64": _b64(_ZPL)})
    assert resp.status_code == 401


def test_upload_and_review_roundtrip(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    device_id, token = _setup(app, client, csrf)
    up = client.post(
        "/api/agent/captures", json={"zpl_b64": _b64(_ZPL)}, headers=_bearer(token)
    )
    assert up.status_code == 201
    cap = up.get_json()["capture"]
    assert cap["device_id"] == device_id
    assert cap["size_bytes"] == len(_ZPL)

    listing = client.get("/api/captures").get_json()["captures"]
    assert [c["id"] for c in listing] == [cap["id"]]
    assert "zpl" not in listing[0]  # list is metadata-only

    full = client.get(f"/api/captures/{cap['id']}").get_json()["capture"]
    assert full["zpl"] == _ZPL

    assert client.delete(f"/api/captures/{cap['id']}", headers=csrf.headers()).status_code == 204
    assert client.get("/api/captures").get_json()["captures"] == []


def test_upload_rejects_non_zpl(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _, token = _setup(app, client, csrf)
    resp = client.post(
        "/api/agent/captures",
        json={"zpl_b64": _b64("<!doctype html><h1>500</h1>")},
        headers=_bearer(token),
    )
    assert resp.status_code == 422
    assert resp.get_json()["error"] == "not_zpl"


def test_upload_rejects_bad_base64(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _, token = _setup(app, client, csrf)
    resp = client.post(
        "/api/agent/captures", json={"zpl_b64": "!!!not-base64!!!"}, headers=_bearer(token)
    )
    assert resp.status_code == 400


def test_captures_are_owner_scoped(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _, token = _setup(app, client, csrf)
    client.post("/api/agent/captures", json={"zpl_b64": _b64(_ZPL)}, headers=_bearer(token))
    cap_id = client.get("/api/captures").get_json()["captures"][0]["id"]

    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        sess = get_session()
        create_user(
            sess, email="other@example.com", plain_password="password123!", role=Role.EDITOR
        )
    client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "password123!"},
        headers=csrf.headers(),
    )
    assert client.get("/api/captures").get_json()["captures"] == []
    assert client.get(f"/api/captures/{cap_id}").status_code == 404


def test_capture_retention_cap(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    from app.services import captures as cap_svc

    device_id, token = _setup(app, client, csrf)
    with app.app_context():
        sess = get_session()
        for i in range(cap_svc.MAX_CAPTURES_PER_DEVICE + 5):
            cap_svc.add_capture(sess, device_id=device_id, zpl=f"^XA^FD{i}^FS^XZ")
    listing = client.get("/api/captures?limit=200").get_json()["captures"]
    assert len(listing) == cap_svc.MAX_CAPTURES_PER_DEVICE
