"""Reusable API helpers — JSON-safe error formatting, etc."""

from __future__ import annotations

import json

from flask import jsonify
from flask.typing import ResponseReturnValue
from pydantic import ValidationError


def validation_error_response(exc: ValidationError) -> ResponseReturnValue:
    """Return a 400 JSON response with serializable validation details.

    `exc.errors()` may include non-JSON-serializable objects (e.g. the original
    ValueError instance under `ctx.error`); going through `exc.json()` and back
    produces a clean, JSON-safe payload.
    """
    detail = json.loads(exc.json())
    return jsonify({"error": "validation_error", "detail": detail}), 400
