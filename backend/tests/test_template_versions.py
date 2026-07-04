"""Template version history (F17): snapshots on manual save, restore."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.services.users import create_user
from tests.conftest import CsrfHelper
from tests.test_templates_endpoints import _seed_format_and_login


def _canvas(text: str) -> dict:
    return {
        "version": 1,
        "stage": {"width_mm": 50, "height_mm": 30},
        "objects": [{"id": "t", "type": "text", "x": 1, "y": 1, "text": text, "fontSize": 4}],
    }


def _mk_template(client: FlaskClient, csrf: CsrfHelper, fmt_id: int) -> int:
    return client.post(
        "/api/templates", json={"name": "Wersjonowany", "format_id": fmt_id}, headers=csrf.headers()
    ).get_json()["id"]


def test_autosave_makes_no_version(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _mk_template(client, csrf, fmt_id)
    # snapshot omitted → autosave
    client.put(f"/api/templates/{tid}", json={"canvas_data": _canvas("a")}, headers=csrf.headers())
    client.put(
        f"/api/templates/{tid}",
        json={"canvas_data": _canvas("b"), "snapshot": False},
        headers=csrf.headers(),
    )
    assert client.get(f"/api/templates/{tid}/versions").get_json()["versions"] == []


def test_manual_save_creates_versions(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _mk_template(client, csrf, fmt_id)
    for text in ("v-one", "v-two", "v-three"):
        client.put(
            f"/api/templates/{tid}",
            json={"canvas_data": _canvas(text), "snapshot": True},
            headers=csrf.headers(),
        )
    versions = client.get(f"/api/templates/{tid}/versions").get_json()["versions"]
    assert [v["version"] for v in versions] == [4, 3, 2]  # newest first (create=1)
    assert all(v["created_by_email"] == "user@example.com" for v in versions)

    # full canvas of an older version is fetchable
    body = client.get(f"/api/templates/{tid}/versions/2").get_json()
    assert body["canvas_data"]["objects"][0]["text"] == "v-one"


def test_restore_sets_canvas_and_records_snapshot(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _mk_template(client, csrf, fmt_id)
    client.put(
        f"/api/templates/{tid}",
        json={"canvas_data": _canvas("original"), "snapshot": True},
        headers=csrf.headers(),
    )  # v2
    client.put(
        f"/api/templates/{tid}",
        json={"canvas_data": _canvas("changed"), "snapshot": True},
        headers=csrf.headers(),
    )  # v3

    restored = client.post(f"/api/templates/{tid}/versions/2/restore", headers=csrf.headers())
    assert restored.status_code == 200
    assert restored.get_json()["canvas_data"]["objects"][0]["text"] == "original"

    versions = client.get(f"/api/templates/{tid}/versions").get_json()["versions"]
    assert versions[0]["note"] == "restored from v2"
    # live template now shows the restored text
    assert client.get(f"/api/templates/{tid}").get_json()["canvas_data"]["objects"][0][
        "text"
    ] == "original"


def test_restore_missing_version_404(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _mk_template(client, csrf, fmt_id)
    assert (
        client.post(f"/api/templates/{tid}/versions/99/restore", headers=csrf.headers()).status_code
        == 404
    )


def test_versions_owner_scoped(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _mk_template(client, csrf, fmt_id)
    client.put(
        f"/api/templates/{tid}",
        json={"canvas_data": _canvas("x"), "snapshot": True},
        headers=csrf.headers(),
    )
    client.put(f"/api/templates/{tid}", json={"is_shared": True}, headers=csrf.headers())

    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        create_user(get_session(), email="other@example.com", plain_password="otherPass123")
    client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "otherPass123"},
        headers=csrf.headers(),
    )
    # shared template is readable, but its history is not
    assert client.get(f"/api/templates/{tid}").status_code == 200
    assert client.get(f"/api/templates/{tid}/versions").status_code == 404
    assert (
        client.post(f"/api/templates/{tid}/versions/2/restore", headers=csrf.headers()).status_code
        == 403
    )


def test_retention_caps_history(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    from app.services import template_versions as tv_svc

    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _mk_template(client, csrf, fmt_id)
    for i in range(tv_svc.MAX_VERSIONS_PER_TEMPLATE + 5):
        client.put(
            f"/api/templates/{tid}",
            json={"canvas_data": _canvas(f"v{i}"), "snapshot": True},
            headers=csrf.headers(),
        )
    versions = client.get(f"/api/templates/{tid}/versions").get_json()["versions"]
    assert len(versions) == tv_svc.MAX_VERSIONS_PER_TEMPLATE
