from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.label_format import FormatKind, LabelFormat
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper


def _seed_format_and_login(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, *, role: Role = Role.EDITOR
) -> int:
    """Insert a label format + an authenticated user, return the format id."""
    with app.app_context():
        sess = get_session()
        fmt = LabelFormat(name="A6", width_mm=105, height_mm=148, kind=FormatKind.A_PAPER)
        sess.add(fmt)
        sess.commit()
        fmt_id = fmt.id
        create_user(sess, email="user@example.com", plain_password="password123!", role=role)
    client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123!"},
        headers=csrf.headers(),
    )
    return fmt_id


def test_list_label_formats_requires_auth(client: FlaskClient) -> None:
    assert client.get("/api/label-formats").status_code == 401


def test_list_label_formats_returns_seed(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _seed_format_and_login(app, client, csrf)
    response = client.get("/api/label-formats")
    assert response.status_code == 200
    formats = response.get_json()["formats"]
    assert any(f["name"] == "A6" for f in formats)


def test_create_template_returns_canvas_data(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    response = client.post(
        "/api/templates",
        json={"name": "My label", "format_id": fmt_id, "canvas_data": {}},
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["name"] == "My label"
    assert body["width_mm"] == 105
    # Service injects an empty stage if none provided
    assert "objects" in body["canvas_data"]
    assert body["canvas_data"]["stage"]["width_mm"] == 105


def test_create_template_with_unknown_format_returns_400(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _seed_format_and_login(app, client, csrf)
    response = client.post(
        "/api/templates",
        json={"name": "Bad", "format_id": 99999},
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_format"


def test_create_template_landscape_swaps_dimensions(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    """Client sends w/h swapped (landscape A6 = 148×105) — Template row +
    empty canvas pick up the override, not the format's portrait values."""
    fmt_id = _seed_format_and_login(app, client, csrf)
    response = client.post(
        "/api/templates",
        json={"name": "Landscape", "format_id": fmt_id, "width_mm": 148, "height_mm": 105},
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["width_mm"] == 148
    assert body["height_mm"] == 105
    assert body["canvas_data"]["stage"]["width_mm"] == 148
    assert body["canvas_data"]["stage"]["height_mm"] == 105


def test_create_template_custom_size(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    """Custom-size flow: any format_id + arbitrary width_mm/height_mm."""
    fmt_id = _seed_format_and_login(app, client, csrf)
    response = client.post(
        "/api/templates",
        json={"name": "Custom", "format_id": fmt_id, "width_mm": 80, "height_mm": 60},
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["width_mm"] == 80
    assert body["height_mm"] == 60


def test_create_template_oversize_dimensions_rejected(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    response = client.post(
        "/api/templates",
        json={"name": "Huge", "format_id": fmt_id, "width_mm": 2000, "height_mm": 100},
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "validation_error"


def test_create_template_no_overrides_falls_back_to_format(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    """Existing flow: no width_mm/height_mm in request → format's preset
    dimensions win (backwards compatibility)."""
    fmt_id = _seed_format_and_login(app, client, csrf)
    response = client.post(
        "/api/templates",
        json={"name": "Default", "format_id": fmt_id},
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["width_mm"] == 105  # _seed_format_and_login uses A6
    assert body["height_mm"] == 148


def test_get_template_returns_full_canvas_data(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    created = client.post(
        "/api/templates",
        json={
            "name": "T1",
            "format_id": fmt_id,
            "canvas_data": {
                "version": 1,
                "stage": {"width_mm": 105, "height_mm": 148},
                "objects": [{"type": "text", "x": 10, "y": 10, "text": "Hi"}],
            },
        },
        headers=csrf.headers(),
    )
    tid = created.get_json()["id"]

    response = client.get(f"/api/templates/{tid}")
    assert response.status_code == 200
    body = response.get_json()
    assert body["canvas_data"]["objects"][0]["text"] == "Hi"


def test_update_template_bumps_version_on_canvas_change(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    created = client.post(
        "/api/templates",
        json={"name": "v", "format_id": fmt_id},
        headers=csrf.headers(),
    )
    tid = created.get_json()["id"]
    assert created.get_json()["version"] == 1

    response = client.put(
        f"/api/templates/{tid}",
        json={"canvas_data": {"version": 1, "stage": {}, "objects": [{"type": "rect"}]}},
        headers=csrf.headers(),
    )
    assert response.status_code == 200
    assert response.get_json()["version"] == 2

    # Renaming alone should NOT bump version
    response = client.put(
        f"/api/templates/{tid}",
        json={"name": "renamed"},
        headers=csrf.headers(),
    )
    assert response.get_json()["version"] == 2


def test_other_user_cannot_access_private_template(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    created = client.post(
        "/api/templates", json={"name": "secret", "format_id": fmt_id}, headers=csrf.headers()
    )
    tid = created.get_json()["id"]

    # Switch to a different account
    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        create_user(get_session(), email="intruder@example.com", plain_password="intrudPass123")
    client.post(
        "/api/auth/login",
        json={"email": "intruder@example.com", "password": "intrudPass123"},
        headers=csrf.headers(),
    )

    assert client.get(f"/api/templates/{tid}").status_code == 403
    assert (
        client.put(f"/api/templates/{tid}", json={"name": "x"}, headers=csrf.headers()).status_code
        == 403
    )
    assert client.delete(f"/api/templates/{tid}", headers=csrf.headers()).status_code == 403


def test_shared_template_visible_to_other_users(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    created = client.post(
        "/api/templates", json={"name": "public", "format_id": fmt_id}, headers=csrf.headers()
    )
    tid = created.get_json()["id"]
    client.put(f"/api/templates/{tid}", json={"is_shared": True}, headers=csrf.headers())

    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        create_user(get_session(), email="other@example.com", plain_password="otherPass123")
    client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "otherPass123"},
        headers=csrf.headers(),
    )

    response = client.get("/api/templates")
    assert response.status_code == 200
    assert any(t["id"] == tid for t in response.get_json()["templates"])

    # And can read the canvas
    assert client.get(f"/api/templates/{tid}").status_code == 200


def test_update_template_dimensions(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    created = client.post(
        "/api/templates", json={"name": "resize me", "format_id": fmt_id}, headers=csrf.headers()
    )
    tid = created.get_json()["id"]

    resp = client.put(
        f"/api/templates/{tid}",
        json={"width_mm": 40, "height_mm": 100},
        headers=csrf.headers(),
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["width_mm"] == 40
    assert body["height_mm"] == 100


def test_update_template_rejects_out_of_range_dimensions(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = client.post(
        "/api/templates", json={"name": "t", "format_id": fmt_id}, headers=csrf.headers()
    ).get_json()["id"]
    # 0 and >1000 mm are rejected by the schema (gt=0, le=1000)
    assert (
        client.put(
            f"/api/templates/{tid}", json={"width_mm": 0}, headers=csrf.headers()
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"/api/templates/{tid}", json={"height_mm": 5000}, headers=csrf.headers()
        ).status_code
        == 400
    )


def test_delete_template_removes_it(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    created = client.post(
        "/api/templates", json={"name": "tmp", "format_id": fmt_id}, headers=csrf.headers()
    )
    tid = created.get_json()["id"]

    assert client.delete(f"/api/templates/{tid}", headers=csrf.headers()).status_code == 204
    assert client.get(f"/api/templates/{tid}").status_code == 404
