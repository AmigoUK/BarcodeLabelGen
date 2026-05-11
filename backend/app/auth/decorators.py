"""Auth/role decorators for route handlers."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from flask import jsonify
from flask.typing import ResponseReturnValue
from flask_login import current_user


def admin_required[F: Callable[..., ResponseReturnValue]](fn: F) -> F:
    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> ResponseReturnValue:
        if not current_user.is_authenticated:
            return jsonify({"error": "unauthorized"}), 401
        if not getattr(current_user, "is_admin", False):
            return jsonify({"error": "forbidden"}), 403
        return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def must_be_active[F: Callable[..., ResponseReturnValue]](fn: F) -> F:
    @wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> ResponseReturnValue:
        if not current_user.is_authenticated:
            return jsonify({"error": "unauthorized"}), 401
        if not getattr(current_user, "is_active", False):
            return jsonify({"error": "account_disabled"}), 403
        return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
