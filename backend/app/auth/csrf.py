"""Double-submit-cookie CSRF protection.

How it works:
  - On any safe request (GET/HEAD/OPTIONS), if the `csrf_token` cookie is
    missing, set it to a fresh random hex value (NOT HttpOnly so JS can read).
  - On any mutating request (POST/PUT/PATCH/DELETE), require that the
    `X-CSRF-Token` header matches the `csrf_token` cookie value. The browser
    sends the cookie automatically; an attacker on another origin can't read
    the cookie to forge the header (same-origin policy), so the check holds.
  - Health endpoint is exempt (used by orchestrators / probes).
"""

from __future__ import annotations

import secrets

from flask import Flask, Response, current_app, jsonify, request

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
EXEMPT_PATHS = frozenset({"/api/health"})
# The connector agent authenticates with a Bearer device token, not a browser
# session — there is no cookie for an attacker to ride, so CSRF doesn't apply.
EXEMPT_PREFIXES = ("/api/agent/",)


def _new_token() -> str:
    return secrets.token_hex(32)


def init_csrf(app: Flask) -> None:
    @app.before_request
    def _enforce_csrf() -> Response | None:
        if request.path in EXEMPT_PATHS:
            return None
        if request.path.startswith(EXEMPT_PREFIXES):
            return None
        if request.method in SAFE_METHODS:
            return None

        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token:
            return _csrf_error("CSRF token missing")
        if not secrets.compare_digest(cookie_token, header_token):
            return _csrf_error("CSRF token mismatch")
        return None

    @app.after_request
    def _ensure_csrf_cookie(response: Response) -> Response:
        # Always seed a token on any response (even health) so the SPA always
        # has a token available regardless of which endpoint loaded first.
        if CSRF_COOKIE_NAME in request.cookies:
            return response
        response.set_cookie(
            CSRF_COOKIE_NAME,
            _new_token(),
            max_age=60 * 60 * 24 * 7,  # 1 week
            secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
            httponly=False,  # JS must read this
            samesite="Lax",
            path="/",
        )
        return response


def _csrf_error(reason: str) -> Response:
    response = jsonify({"error": "csrf_failed", "detail": reason})
    response.status_code = 403
    return response


def rotate_csrf_cookie(response: Response, *, secure: bool) -> Response:
    """Force a fresh CSRF token (call on login + logout)."""
    response.set_cookie(
        CSRF_COOKIE_NAME,
        _new_token(),
        max_age=60 * 60 * 24 * 7,
        secure=secure,
        httponly=False,
        samesite="Lax",
        path="/",
    )
    return response
