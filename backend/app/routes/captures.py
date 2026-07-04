"""Captured-ZPL inbox endpoints (session auth)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required

from app.db.session import get_session
from app.schemas.device import CapturePublic
from app.services import captures as cap_svc

captures_bp = Blueprint("captures", __name__)


@captures_bp.get("/captures")
@login_required
def list_captures() -> ResponseReturnValue:
    limit = min(request.args.get("limit", default=100, type=int) or 100, 200)
    session = get_session()
    captures = cap_svc.list_captures_for_user(session, user_id=current_user.id, limit=limit)
    return jsonify(
        {"captures": [CapturePublic.model_validate(c).model_dump(mode="json") for c in captures]}
    )


@captures_bp.get("/captures/<int:capture_id>")
@login_required
def get_capture(capture_id: int) -> ResponseReturnValue:
    session = get_session()
    try:
        capture = cap_svc.get_capture_for_user(session, capture_id, user_id=current_user.id)
    except cap_svc.CaptureNotFoundError:
        return jsonify({"error": "capture_not_found"}), 404
    body = CapturePublic.model_validate(capture).model_dump(mode="json")
    body["zpl"] = capture.zpl
    return jsonify({"capture": body})


@captures_bp.delete("/captures/<int:capture_id>")
@login_required
def delete_capture(capture_id: int) -> ResponseReturnValue:
    session = get_session()
    try:
        cap_svc.delete_capture(session, capture_id, user_id=current_user.id)
    except cap_svc.CaptureNotFoundError:
        return jsonify({"error": "capture_not_found"}), 404
    return "", 204
