"""Auth endpoints: login, logout, change-password."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, make_response, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required, login_user, logout_user
from pydantic import ValidationError

from app.api_helpers import validation_error_response
from app.auth.csrf import rotate_csrf_cookie
from app.db.session import get_session
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.schemas.user import UserPublic
from app.services.users import authenticate, change_own_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/login")
def login() -> ResponseReturnValue:
    try:
        payload = LoginRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    user = authenticate(session, payload.email, payload.password)
    if user is None:
        return jsonify({"error": "invalid_credentials"}), 401

    login_user(user, remember=False)

    response = make_response(
        jsonify(
            {
                "user": UserPublic.model_validate(user).model_dump(mode="json"),
            }
        )
    )
    rotate_csrf_cookie(response, secure=current_app.config.get("SESSION_COOKIE_SECURE", False))
    return response


@auth_bp.post("/auth/logout")
@login_required
def logout() -> ResponseReturnValue:
    logout_user()
    response = make_response(jsonify({"status": "logged_out"}))
    rotate_csrf_cookie(response, secure=current_app.config.get("SESSION_COOKIE_SECURE", False))
    return response


@auth_bp.post("/auth/change-password")
@login_required
def change_password() -> ResponseReturnValue:
    try:
        payload = ChangePasswordRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    if payload.current_password == payload.new_password:
        return jsonify({"error": "new_password_must_differ"}), 400

    session = get_session()
    ok = change_own_password(
        session,
        current_user,
        current_plain=payload.current_password,
        new_plain=payload.new_password,
    )
    if not ok:
        return jsonify({"error": "invalid_current_password"}), 400

    return jsonify({"status": "password_changed"})
