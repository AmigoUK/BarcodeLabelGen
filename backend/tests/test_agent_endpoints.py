"""HTTP tests for /api/agent/* (Bearer device-token auth, CSRF-exempt)."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper


def _setup(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> tuple[int, str]:
    """User + device; returns (device_id, plaintext token)."""
    with app.app_context():
        sess = get_session()
        create_user(
            sess, email="agent@example.com", plain_password="password123!", role=Role.EDITOR
        )
    client.post(
        "/api/auth/login",
        json={"email": "agent@example.com", "password": "password123!"},
        headers=csrf.headers(),
    )
    body = client.post("/api/devices", json={"name": "Hala"}, headers=csrf.headers()).get_json()
    return body["device"]["id"], body["token"]


def _queue_job(client: FlaskClient, csrf: CsrfHelper, device_id: int) -> int:
    resp = client.post(
        "/api/print-jobs",
        json={"device_id": device_id, "printer": "Zebra-1", "zpl": "^XA^FDjob^FS^XZ"},
        headers=csrf.headers(),
    )
    return resp.get_json()["job"]["id"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_agent_requires_token(client: FlaskClient) -> None:
    assert client.get("/api/agent/jobs").status_code == 401
    assert client.get("/api/agent/jobs", headers=_bearer("blg_wrong")).status_code == 401


def test_agent_poll_claims_jobs_once(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    device_id, token = _setup(app, client, csrf)
    job_id = _queue_job(client, csrf, device_id)

    first = client.get("/api/agent/jobs", headers=_bearer(token)).get_json()["jobs"]
    assert [j["id"] for j in first] == [job_id]
    assert first[0]["zpl"] == "^XA^FDjob^FS^XZ"
    # Second poll: nothing pending anymore (claimed → sent)
    assert client.get("/api/agent/jobs", headers=_bearer(token)).get_json()["jobs"] == []
    # User's list shows the job as sent
    jobs = client.get("/api/print-jobs").get_json()["jobs"]
    assert jobs[0]["status"] == "sent"
    assert jobs[0]["sent_at"] is not None


def test_agent_status_report_no_csrf_needed(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    device_id, token = _setup(app, client, csrf)
    job_id = _queue_job(client, csrf, device_id)
    client.get("/api/agent/jobs", headers=_bearer(token))

    # POST without any CSRF header — must pass (agent path is exempt)
    resp = client.post(
        f"/api/agent/jobs/{job_id}/status", json={"status": "done"}, headers=_bearer(token)
    )
    assert resp.status_code == 200
    assert client.get("/api/print-jobs").get_json()["jobs"][0]["status"] == "done"


def test_agent_error_report(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    device_id, token = _setup(app, client, csrf)
    job_id = _queue_job(client, csrf, device_id)
    client.get("/api/agent/jobs", headers=_bearer(token))
    client.post(
        f"/api/agent/jobs/{job_id}/status",
        json={"status": "error", "error": "printer unreachable"},
        headers=_bearer(token),
    )
    job = client.get("/api/print-jobs").get_json()["jobs"][0]
    assert job["status"] == "error"
    assert job["error"] == "printer unreachable"


def test_agent_cannot_touch_foreign_job(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    device_id, token = _setup(app, client, csrf)
    job_id = _queue_job(client, csrf, device_id)
    # Second device of the same user — its token must not ack device 1's job
    body2 = client.post("/api/devices", json={"name": "Biuro"}, headers=csrf.headers()).get_json()
    resp = client.post(
        f"/api/agent/jobs/{job_id}/status",
        json={"status": "done"},
        headers=_bearer(body2["token"]),
    )
    assert resp.status_code == 404


def test_agent_state_updates_device(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _device_id, token = _setup(app, client, csrf)
    resp = client.post(
        "/api/agent/state",
        json={
            "agent_version": "0.1.0",
            "printers": [{"name": "Zebra-1", "host": "192.168.1.50", "port": 9100}],
        },
        headers=_bearer(token),
    )
    assert resp.status_code == 200
    device = client.get("/api/devices").get_json()["devices"][0]
    assert device["agent_version"] == "0.1.0"
    assert device["printers"] == [{"name": "Zebra-1", "host": "192.168.1.50", "port": 9100}]
    assert device["last_seen_at"] is not None
