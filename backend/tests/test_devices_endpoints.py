"""HTTP tests for /api/devices and /api/print-jobs (session auth)."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper


def _login(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, *, email: str = "dev@example.com"
) -> None:
    with app.app_context():
        sess = get_session()
        create_user(sess, email=email, plain_password="password123!", role=Role.EDITOR)
    client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123!"},
        headers=csrf.headers(),
    )


def _create_device(client: FlaskClient, csrf: CsrfHelper, name: str = "Magazyn") -> dict:
    resp = client.post("/api/devices", json={"name": name}, headers=csrf.headers())
    assert resp.status_code == 201
    return resp.get_json()


def test_devices_require_auth(client: FlaskClient, csrf: CsrfHelper) -> None:
    assert client.get("/api/devices").status_code == 401
    assert (
        client.post("/api/devices", json={"name": "x"}, headers=csrf.headers()).status_code == 401
    )


def test_create_device_returns_token_once(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    body = _create_device(client, csrf)
    assert body["token"].startswith("blg_")
    assert len(body["token"]) == 4 + 64
    assert body["device"]["name"] == "Magazyn"
    # Token is not retrievable from the list endpoint
    listing = client.get("/api/devices").get_json()
    assert len(listing["devices"]) == 1
    assert "token" not in listing["devices"][0]
    assert "token_hash" not in listing["devices"][0]


def test_duplicate_device_name_conflicts(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    _create_device(client, csrf, "Biuro")
    resp = client.post("/api/devices", json={"name": "Biuro"}, headers=csrf.headers())
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "device_name_taken"


def test_delete_device(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    device_id = _create_device(client, csrf)["device"]["id"]
    assert client.delete(f"/api/devices/{device_id}", headers=csrf.headers()).status_code == 204
    assert client.get("/api/devices").get_json()["devices"] == []


def test_create_print_job_and_list(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    device_id = _create_device(client, csrf)["device"]["id"]
    resp = client.post(
        "/api/print-jobs",
        json={"device_id": device_id, "printer": "Zebra-1", "zpl": "^XA^FDtest^FS^XZ", "copies": 2},
        headers=csrf.headers(),
    )
    assert resp.status_code == 201
    job = resp.get_json()["job"]
    assert job["status"] == "pending"
    assert job["copies"] == 2
    assert "zpl" not in job  # payload only exposed to the agent

    jobs = client.get("/api/print-jobs").get_json()["jobs"]
    assert [j["id"] for j in jobs] == [job["id"]]


def test_print_job_rejects_foreign_device(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    device_id = _create_device(client, csrf)["device"]["id"]
    # Second user can't queue to the first user's device
    client.post("/api/auth/logout", headers=csrf.headers())
    _login(app, client, csrf, email="other@example.com")
    resp = client.post(
        "/api/print-jobs",
        json={"device_id": device_id, "printer": "Zebra-1", "zpl": "^XA^XZ"},
        headers=csrf.headers(),
    )
    assert resp.status_code == 404


def test_print_job_rejects_non_zpl(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf, email="zplval@example.com")
    device_id = _create_device(client, csrf, "Walidacja")["device"]["id"]
    resp = client.post(
        "/api/print-jobs",
        json={"device_id": device_id, "printer": "Zebra-1", "zpl": "<!doctype html><h1>500</h1>"},
        headers=csrf.headers(),
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["error"] == "invalid_zpl"
    assert "HTML" in body["detail"]
