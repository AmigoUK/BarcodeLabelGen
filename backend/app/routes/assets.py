"""Image asset upload + serve."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, send_file
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required

from app.db.session import get_session
from app.schemas.template import AssetPublic
from app.services import assets as asset_svc

assets_bp = Blueprint("assets", __name__)


@assets_bp.post("/assets/images")
@login_required
def upload_image() -> ResponseReturnValue:
    file = request.files.get("file")
    if file is None or file.filename is None:
        return jsonify({"error": "no_file"}), 400

    raw = file.read()
    declared_mime = file.mimetype or "application/octet-stream"

    session = get_session()
    try:
        asset = asset_svc.save_image(
            session,
            owner_id=current_user.id,
            original_filename=file.filename,
            raw=raw,
            declared_mime=declared_mime,
        )
    except asset_svc.AssetUploadError as exc:
        return jsonify({"error": "upload_rejected", "detail": str(exc)}), 400

    return jsonify(AssetPublic.model_validate(asset).model_dump(mode="json")), 201


@assets_bp.get("/assets/images/<int:asset_id>")
@login_required
def serve_image(asset_id: int) -> ResponseReturnValue:
    session = get_session()
    asset = asset_svc.get_asset(session, asset_id)
    if asset is None:
        return jsonify({"error": "asset_not_found"}), 404
    # Owners and admins can fetch; otherwise we'd leak someone else's images.
    if asset.owner_id != current_user.id and not getattr(current_user, "is_admin", False):
        return jsonify({"error": "forbidden"}), 403

    file_path = asset_svc.assets_dir() / asset.storage_filename
    if not file_path.is_file():
        return jsonify({"error": "asset_file_missing"}), 410

    from app.api_helpers import harden_image_response

    return harden_image_response(send_file(file_path, mimetype=asset.mime_type, conditional=True))


@assets_bp.get("/assets/images")
@login_required
def list_images() -> ResponseReturnValue:
    session = get_session()
    items = asset_svc.list_user_assets(session, owner_id=current_user.id)
    return jsonify(
        {"assets": [AssetPublic.model_validate(a).model_dump(mode="json") for a in items]}
    )
