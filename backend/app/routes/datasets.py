"""Dataset upload + preview + filter endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import ValidationError

from app.api_helpers import validation_error_response
from app.db.session import get_session
from app.schemas.dataset import DataSetPublic, FilterRequest, FilterResponse
from app.services import datasets as ds_svc

datasets_bp = Blueprint("datasets", __name__)


@datasets_bp.get("/datasets")
@login_required
def list_datasets() -> ResponseReturnValue:
    session = get_session()
    items = ds_svc.list_user_datasets(session, owner_id=current_user.id)
    return jsonify(
        {"datasets": [DataSetPublic.model_validate(d).model_dump(mode="json") for d in items]}
    )


@datasets_bp.post("/datasets")
@login_required
def upload_dataset() -> ResponseReturnValue:
    file = request.files.get("file")
    if file is None or file.filename is None:
        return jsonify({"error": "no_file"}), 400

    raw = file.read()
    session = get_session()
    try:
        ds = ds_svc.save_upload(
            session,
            owner_id=current_user.id,
            original_filename=file.filename,
            raw=raw,
        )
    except ds_svc.DataSetUploadError as exc:
        return jsonify({"error": "upload_rejected", "detail": str(exc)}), 400

    return jsonify(DataSetPublic.model_validate(ds).model_dump(mode="json")), 201


@datasets_bp.get("/datasets/<int:dataset_id>")
@login_required
def get_dataset(dataset_id: int) -> ResponseReturnValue:
    session = get_session()
    ds = ds_svc.get_dataset(session, dataset_id)
    if ds is None or ds.owner_id != current_user.id:
        return jsonify({"error": "dataset_not_found"}), 404
    return jsonify(DataSetPublic.model_validate(ds).model_dump(mode="json"))


@datasets_bp.delete("/datasets/<int:dataset_id>")
@login_required
def delete_dataset(dataset_id: int) -> ResponseReturnValue:
    session = get_session()
    ds = ds_svc.get_dataset(session, dataset_id)
    if ds is None or ds.owner_id != current_user.id:
        return jsonify({"error": "dataset_not_found"}), 404
    ds_svc.delete_dataset(session, dataset_id)
    return "", 204


@datasets_bp.get("/datasets/<int:dataset_id>/preview")
@login_required
def preview_dataset(dataset_id: int) -> ResponseReturnValue:
    session = get_session()
    ds = ds_svc.get_dataset(session, dataset_id)
    if ds is None or ds.owner_id != current_user.id:
        return jsonify({"error": "dataset_not_found"}), 404
    try:
        limit = max(1, min(int(request.args.get("rows", "5")), 100))
    except ValueError:
        limit = 5
    return jsonify({"rows": ds_svc.preview_rows(ds, limit=limit), "total": ds.row_count})


@datasets_bp.post("/datasets/<int:dataset_id>/filter")
@login_required
def filter_dataset(dataset_id: int) -> ResponseReturnValue:
    session = get_session()
    ds = ds_svc.get_dataset(session, dataset_id)
    if ds is None or ds.owner_id != current_user.id:
        return jsonify({"error": "dataset_not_found"}), 404

    try:
        payload = FilterRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    rows = ds_svc.load_rows(ds)
    matched = ds_svc.apply_filter(rows, column=payload.column, op=payload.op, value=payload.value)
    response = FilterResponse(match_count=len(matched), preview=matched[:5])
    return jsonify(response.model_dump(mode="json"))
