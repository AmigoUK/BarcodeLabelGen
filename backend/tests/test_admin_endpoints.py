from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper


def _login_as(app: Flask, client: FlaskClient, csrf: CsrfHelper, role: Role) -> None:
    email = "actor@example.com"
    password = "actorPassword123"
    with app.app_context():
        create_user(get_session(), email=email, plain_password=password, role=role)
    client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=csrf.headers(),
    )


def test_admin_can_list_users(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login_as(app, client, csrf, Role.ADMIN)
    response = client.get("/api/admin/users")
    assert response.status_code == 200
    users = response.get_json()["users"]
    assert any(u["role"] == "admin" for u in users)


def test_non_admin_cannot_list_users(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login_as(app, client, csrf, Role.EDITOR)
    response = client.get("/api/admin/users")
    assert response.status_code == 403


def test_unauthenticated_cannot_list_users(client: FlaskClient) -> None:
    response = client.get("/api/admin/users")
    assert response.status_code == 401


def test_admin_can_create_user(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login_as(app, client, csrf, Role.ADMIN)
    response = client.post(
        "/api/admin/users",
        json={
            "email": "new@example.com",
            "role": "editor",
            "language": "pl",
            "temporary_password": "tempPassword123",
        },
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["must_change_password"] is True
    assert body["temporary_password"] == "tempPassword123"


def test_create_user_duplicate_email_returns_409(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login_as(app, client, csrf, Role.ADMIN)
    payload = {"email": "dup@example.com", "temporary_password": "tempPassword123"}
    client.post("/api/admin/users", json=payload, headers=csrf.headers())
    response = client.post("/api/admin/users", json=payload, headers=csrf.headers())
    assert response.status_code == 409
    assert response.get_json()["error"] == "email_already_exists"


def test_admin_can_update_user_role(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login_as(app, client, csrf, Role.ADMIN)
    create_response = client.post(
        "/api/admin/users",
        json={"email": "promote@example.com", "temporary_password": "tempPassword123"},
        headers=csrf.headers(),
    )
    new_id = create_response.get_json()["user"]["id"]

    response = client.patch(
        f"/api/admin/users/{new_id}",
        json={"role": "admin"},
        headers=csrf.headers(),
    )
    assert response.status_code == 200
    assert response.get_json()["role"] == "admin"


def test_admin_cannot_disable_self(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login_as(app, client, csrf, Role.ADMIN)
    me_id = client.get("/api/me").get_json()["id"]

    response = client.patch(
        f"/api/admin/users/{me_id}",
        json={"is_active": False},
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "cannot_disable_self"


def test_admin_can_reset_user_password(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login_as(app, client, csrf, Role.ADMIN)
    create_response = client.post(
        "/api/admin/users",
        json={"email": "reset@example.com", "temporary_password": "originalPassword123"},
        headers=csrf.headers(),
    )
    target_id = create_response.get_json()["user"]["id"]

    response = client.post(
        f"/api/admin/users/{target_id}/reset-password",
        json={"new_temporary_password": "freshTemp789"},
        headers=csrf.headers(),
    )
    assert response.status_code == 200
    assert response.get_json()["temporary_password"] == "freshTemp789"


def test_update_unknown_user_returns_404(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login_as(app, client, csrf, Role.ADMIN)
    response = client.patch(
        "/api/admin/users/999999",
        json={"role": "viewer"},
        headers=csrf.headers(),
    )
    assert response.status_code == 404
