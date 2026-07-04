"""Connector-agent endpoints (Bearer device token, no session, no CSRF).

The agent polls for work and reports back:
  GET  /api/agent/jobs             → claim pending jobs (marked `sent`)
  POST /api/agent/jobs/<id>/status → done | error after printing
  POST /api/agent/state            → printer list + agent version heartbeat
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from pydantic import ValidationError

from app.api_helpers import validation_error_response
from app.auth.device import current_device, device_token_required
from app.db.session import get_session
from app.models.print_job import PrintJobStatus
from app.schemas.device import AgentJobPayload, AgentStateRequest, AgentStatusRequest
from app.services import print_jobs as pj_svc

agent_bp = Blueprint("agent", __name__)


@agent_bp.get("/agent/jobs")
@device_token_required
def poll_jobs() -> ResponseReturnValue:
    session = get_session()
    jobs = pj_svc.claim_pending_jobs(session, device_id=current_device().id)
    return jsonify(
        {"jobs": [AgentJobPayload.model_validate(j).model_dump(mode="json") for j in jobs]}
    )


@agent_bp.post("/agent/jobs/<int:job_id>/status")
@device_token_required
def report_job_status(job_id: int) -> ResponseReturnValue:
    try:
        payload = AgentStatusRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        job = pj_svc.report_status(
            session,
            job_id,
            device_id=current_device().id,
            status=PrintJobStatus(payload.status),
            error=payload.error,
        )
    except pj_svc.PrintJobNotFoundError:
        return jsonify({"error": "job_not_found"}), 404
    return jsonify({"id": job.id, "status": job.status.value})


@agent_bp.post("/agent/state")
@device_token_required
def report_state() -> ResponseReturnValue:
    try:
        payload = AgentStateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    device = current_device()
    device.agent_version = payload.agent_version
    device.printers = [p.model_dump() for p in payload.printers]
    session.commit()
    return jsonify({"ok": True})
