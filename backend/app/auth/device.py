"""Bearer-token authentication for the connector agent (/api/agent/*).

The agent sends `Authorization: Bearer blg_<hex>`; we look the device up by
the SHA-256 digest of the whole token. No session, no CSRF (see csrf.py
EXEMPT_PREFIXES). The matched Device lands in flask.g for the view, and
`last_seen_at` is refreshed on every authenticated call.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps

from flask import g, jsonify, request
from flask.typing import ResponseReturnValue

from app.db.session import get_session
from app.models.device import Device

TOKEN_PREFIX = "blg_"  # noqa: S105 — token *prefix*, not a secret


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_device() -> Device:
    return g.device  # type: ignore[no-any-return]


def device_token_required[F: Callable[..., ResponseReturnValue]](func: F) -> F:
    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> ResponseReturnValue:
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            return jsonify({"error": "unauthorized", "detail": "missing bearer token"}), 401

        session = get_session()
        device = (
            session.query(Device).filter(Device.token_hash == hash_token(token.strip())).first()
        )
        if device is None:
            return jsonify({"error": "unauthorized", "detail": "unknown device token"}), 401

        device.last_seen_at = datetime.now(UTC)
        session.commit()
        g.device = device
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
