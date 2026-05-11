"""Current user profile endpoint."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required

from app.schemas.user import UserPublic

me_bp = Blueprint("me", __name__)


@me_bp.get("/me")
@login_required
def me() -> ResponseReturnValue:
    return jsonify(UserPublic.model_validate(current_user).model_dump(mode="json"))
