"""Print-queue endpoints (session auth) — submit ZPL to a connector device."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import ValidationError

from app.api_helpers import validation_error_response
from app.db.session import get_session
from app.schemas.device import PrintJobCreateRequest, PrintJobPublic
from app.services import devices as dev_svc
from app.services import print_jobs as pj_svc

print_jobs_bp = Blueprint("print_jobs", __name__)


@print_jobs_bp.post("/print-jobs")
@login_required
def create_print_job() -> ResponseReturnValue:
    try:
        payload = PrintJobCreateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        device = dev_svc.get_owned_device(
            session,
            payload.device_id,
            owner_id=current_user.id,
            is_admin=getattr(current_user, "is_admin", False),
        )
    except dev_svc.DeviceNotFoundError:
        return jsonify({"error": "device_not_found"}), 404

    job = pj_svc.create_job(
        session,
        device_id=device.id,
        created_by=current_user.id,
        printer=payload.printer,
        zpl=payload.zpl,
        copies=payload.copies,
    )
    return jsonify({"job": PrintJobPublic.model_validate(job).model_dump(mode="json")}), 201


@print_jobs_bp.get("/print-jobs")
@login_required
def list_print_jobs() -> ResponseReturnValue:
    limit = min(request.args.get("limit", default=50, type=int) or 50, 200)
    session = get_session()
    jobs = pj_svc.list_jobs_for_user(session, user_id=current_user.id, limit=limit)
    return jsonify(
        {"jobs": [PrintJobPublic.model_validate(j).model_dump(mode="json") for j in jobs]}
    )
