from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper


def _seed(app: Flask, *, role: Role = Role.EDITOR) -> tuple[str, str]:
    email = "user@example.com"
    password = "initialPassword123"
    with app.app_context():
        create_user(get_session(), email=email, plain_password=password, role=role)
    return email, password


def test_login_success_returns_user_payload(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    email, password = _seed(app)
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=csrf.headers(),
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["user"]["email"] == email
    assert body["user"]["must_change_password"] is True


def test_login_wrong_password_returns_401(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    email, _password = _seed(app)
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrong"},
        headers=csrf.headers(),
    )
    assert response.status_code == 401
    assert response.get_json()["error"] == "invalid_credentials"


def test_login_invalid_email_format_returns_400(client: FlaskClient, csrf: CsrfHelper) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "not-an-email", "password": "anything"},
        headers=csrf.headers(),
    )
    assert response.status_code == 400


def test_post_without_csrf_token_returns_403(client: FlaskClient) -> None:
    # No prior request → no csrf cookie → no header → must fail
    response = client.post(
        "/api/auth/login",
        json={"email": "x@example.com", "password": "y"},
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "csrf_failed"


def test_me_requires_authentication(client: FlaskClient) -> None:
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_returns_logged_in_user(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    email, password = _seed(app)
    client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=csrf.headers(),
    )

    response = client.get("/api/me")
    assert response.status_code == 200
    assert response.get_json()["email"] == email


def test_logout_clears_session(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    email, password = _seed(app)
    client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=csrf.headers(),
    )
    assert client.get("/api/me").status_code == 200

    response = client.post("/api/auth/logout", headers=csrf.headers())
    assert response.status_code == 200

    assert client.get("/api/me").status_code == 401


def test_change_password_flow(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    email, password = _seed(app)
    client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=csrf.headers(),
    )

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": password, "new_password": "brandNewPassword456"},
        headers=csrf.headers(),
    )
    assert response.status_code == 200

    client.post("/api/auth/logout", headers=csrf.headers())
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "brandNewPassword456"},
        headers=csrf.headers(),
    )
    assert response.status_code == 200
    assert response.get_json()["user"]["must_change_password"] is False


def test_change_password_rejects_same_password(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    email, password = _seed(app)
    client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=csrf.headers(),
    )
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": password, "new_password": password},
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "new_password_must_differ"
