"""Reusable API helpers — JSON-safe error formatting, etc."""

from __future__ import annotations

import json

from flask import Response, jsonify
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


def harden_image_response(response: Response) -> Response:
    """Neutralize stored XSS on user-uploaded image endpoints.

    PNG/JPEG are re-encoded at upload, but SVG passes through verbatim and
    may embed <script>. Rendering via <img> never runs scripts; the attack
    is direct navigation to the image URL in our origin — these headers
    (CSP sandbox + nosniff) block script execution there while leaving
    <img> thumbnails untouched."""
    response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
