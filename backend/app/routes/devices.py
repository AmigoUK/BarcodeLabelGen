"""Device management endpoints (session auth) — Settings → Devices."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import ValidationError

from app.api_helpers import validation_error_response
from app.db.session import get_session
from app.schemas.device import DeviceCreateRequest, DevicePublic
from app.services import devices as dev_svc

devices_bp = Blueprint("devices", __name__)


@devices_bp.get("/devices")
@login_required
def list_devices() -> ResponseReturnValue:
    session = get_session()
    devices = dev_svc.list_devices(session, owner_id=current_user.id)
    return jsonify(
        {"devices": [DevicePublic.model_validate(d).model_dump(mode="json") for d in devices]}
    )


@devices_bp.post("/devices")
@login_required
def create_device() -> ResponseReturnValue:
    try:
        payload = DeviceCreateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        device, token = dev_svc.create_device(
            session, owner_id=current_user.id, name=payload.name.strip()
        )
    except dev_svc.DeviceNameTakenError:
        return jsonify({"error": "device_name_taken"}), 409

    # The plaintext token is returned exactly once — it is never retrievable
    # again (only its hash is stored).
    return jsonify(
        {"device": DevicePublic.model_validate(device).model_dump(mode="json"), "token": token}
    ), 201


@devices_bp.delete("/devices/<int:device_id>")
@login_required
def delete_device(device_id: int) -> ResponseReturnValue:
    session = get_session()
    try:
        dev_svc.delete_device(
            session,
            device_id,
            owner_id=current_user.id,
            is_admin=getattr(current_user, "is_admin", False),
        )
    except dev_svc.DeviceNotFoundError:
        return jsonify({"error": "device_not_found"}), 404
    return "", 204
