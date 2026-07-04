"""Template-folder endpoints (session auth, owner-scoped)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import BaseModel, Field, ValidationError

from app.api_helpers import validation_error_response
from app.db.session import get_session
from app.models.folder import Folder
from app.services import folders as folder_svc

folders_bp = Blueprint("folders", __name__)

_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=_COLOR_PATTERN)


class FolderPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    # Explicit null clears the colour; absent = no change.
    color: str | None = Field(default=None, pattern=_COLOR_PATTERN)


def _public(folder: Folder, count: int | None) -> dict:
    return {
        "id": folder.id,
        "name": folder.name,
        "color": folder.color,
        "template_count": count,
        "created_at": folder.created_at.isoformat(),
    }


@folders_bp.get("/folders")
@login_required
def list_folders() -> ResponseReturnValue:
    session = get_session()
    rows = folder_svc.list_folders(session, owner_id=current_user.id)
    return jsonify({"folders": [_public(f, c) for f, c in rows]})


@folders_bp.post("/folders")
@login_required
def create_folder() -> ResponseReturnValue:
    try:
        payload = FolderCreateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)
    session = get_session()
    try:
        folder = folder_svc.create_folder(
            session, owner_id=current_user.id, name=payload.name.strip(), color=payload.color
        )
    except folder_svc.FolderNameTakenError:
        return jsonify({"error": "folder_name_taken"}), 409
    return jsonify({"folder": _public(folder, 0)}), 201


@folders_bp.patch("/folders/<int:folder_id>")
@login_required
def update_folder(folder_id: int) -> ResponseReturnValue:
    try:
        payload = FolderPatchRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)
    session = get_session()
    try:
        folder = folder_svc.update_folder(
            session,
            folder_id,
            owner_id=current_user.id,
            name=payload.name.strip() if payload.name else None,
            color=payload.color,
            color_set="color" in payload.model_fields_set,
        )
    except folder_svc.FolderNotFoundError:
        return jsonify({"error": "folder_not_found"}), 404
    except folder_svc.FolderNameTakenError:
        return jsonify({"error": "folder_name_taken"}), 409
    return jsonify({"folder": _public(folder, None)})


@folders_bp.delete("/folders/<int:folder_id>")
@login_required
def delete_folder(folder_id: int) -> ResponseReturnValue:
    session = get_session()
    try:
        folder_svc.delete_folder(session, folder_id, owner_id=current_user.id)
    except folder_svc.FolderNotFoundError:
        return jsonify({"error": "folder_not_found"}), 404
    return "", 204
