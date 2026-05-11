"""PDF generation endpoint.

For Sprint 4 this is the single-label version: POST /api/generate with
{"template_id": N} renders the template's canvas exactly as the user
designed it and returns application/pdf. Sprint 5 will extend the same
endpoint with a `dataset_id` + `mapping` for batch generation.
"""

from __future__ import annotations

import re
from typing import Any

from flask import Blueprint, Response, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import BaseModel, ValidationError

from app.api_helpers import validation_error_response
from app.db.session import get_session
from app.models.asset import Asset
from app.services import templates as tpl_svc
from app.services.pdf_renderer import PdfRenderError, render_template_pdf

generate_bp = Blueprint("generate", __name__)


_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class GenerateRequest(BaseModel):
    template_id: int


@generate_bp.post("/generate")
@login_required
def generate_pdf() -> ResponseReturnValue:
    try:
        payload = GenerateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        tpl = tpl_svc.get(session, payload.template_id, requesting_user_id=current_user.id)
    except tpl_svc.TemplateNotFoundError:
        return jsonify({"error": "template_not_found"}), 404
    except tpl_svc.TemplateAccessError:
        return jsonify({"error": "forbidden"}), 403

    def _resolve_asset(asset_id: int) -> Asset | None:
        asset = session.get(Asset, asset_id)
        if asset is None:
            return None
        # Only own assets — refuse to embed someone else's image even if the
        # template references it.
        if asset.owner_id != current_user.id and not getattr(current_user, "is_admin", False):
            return None
        return asset

    canvas_data: dict[str, Any] = dict(tpl.canvas_data) if tpl.canvas_data else {}

    try:
        pdf_bytes = render_template_pdf(
            canvas_data,
            width_mm=float(tpl.width_mm),
            height_mm=float(tpl.height_mm),
            resolve_asset=_resolve_asset,
        )
    except PdfRenderError as exc:
        return jsonify({"error": "pdf_render_failed", "detail": str(exc)}), 500

    safe = _SAFE_FILENAME.sub("_", tpl.name).strip("_") or f"template_{tpl.id}"
    filename = f"{safe}.pdf"

    response = Response(pdf_bytes, mimetype="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Cache-Control"] = "no-store"
    return response
