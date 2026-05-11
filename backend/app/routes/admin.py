"""Admin endpoints: user management."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import ValidationError

from app.api_helpers import validation_error_response
from app.auth.decorators import admin_required
from app.db.session import get_session
from app.schemas.user import (
    CreateUserRequest,
    CreateUserResponse,
    ResetPasswordRequest,
    UpdateUserRequest,
    UserPublic,
)
from app.services.users import (
    EmailAlreadyExistsError,
    UserNotFoundError,
    create_user,
    list_users,
    reset_password,
    update_user,
)

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/admin/users")
@login_required
@admin_required
def list_all_users() -> ResponseReturnValue:
    session = get_session()
    users = list_users(session)
    return jsonify({"users": [UserPublic.model_validate(u).model_dump(mode="json") for u in users]})


@admin_bp.post("/admin/users")
@login_required
@admin_required
def create_new_user() -> ResponseReturnValue:
    try:
        payload = CreateUserRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        user = create_user(
            session,
            email=payload.email,
            plain_password=payload.temporary_password,
            role=payload.role,
            language=payload.language,
            must_change_password=True,
        )
    except EmailAlreadyExistsError:
        return jsonify({"error": "email_already_exists"}), 409

    body = CreateUserResponse(
        user=UserPublic.model_validate(user),
        temporary_password=payload.temporary_password,
    )
    return jsonify(body.model_dump(mode="json")), 201


@admin_bp.patch("/admin/users/<int:user_id>")
@login_required
@admin_required
def update_existing_user(user_id: int) -> ResponseReturnValue:
    try:
        payload = UpdateUserRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    if user_id == current_user.id and payload.is_active is False:
        return jsonify({"error": "cannot_disable_self"}), 400

    session = get_session()
    try:
        user = update_user(
            session,
            user_id,
            role=payload.role,
            is_active=payload.is_active,
            language=payload.language,
        )
    except UserNotFoundError:
        return jsonify({"error": "user_not_found"}), 404

    return jsonify(UserPublic.model_validate(user).model_dump(mode="json"))


@admin_bp.post("/admin/users/<int:user_id>/reset-password")
@login_required
@admin_required
def admin_reset_password(user_id: int) -> ResponseReturnValue:
    try:
        payload = ResetPasswordRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        user = reset_password(session, user_id, payload.new_temporary_password)
    except UserNotFoundError:
        return jsonify({"error": "user_not_found"}), 404

    return jsonify(
        {
            "user": UserPublic.model_validate(user).model_dump(mode="json"),
            "temporary_password": payload.new_temporary_password,
        }
    )
