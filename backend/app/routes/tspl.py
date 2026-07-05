"""HTTP endpoint for TSPL export (single-label / template mode).

Mirrors the ZPL generate endpoint's `mode="template"` branch: resolve the
canvas (live editor or saved template), evaluate {{date+x}} placeholders,
render TSPL, and return it as a downloadable attachment.
"""

from __future__ import annotations

import json
from typing import Any

from flask import Blueprint, Response, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import BaseModel, ValidationError

from app.api_helpers import validation_error_response
from app.db.session import get_session
from app.routes.generate import _safe_filename
from app.services import templates as tpl_svc
from app.services.placeholders import substitute_dates_in_canvas
from app.services.tspl import generate_tspl
from app.services.zpl.units import dpmm_for_dpi

tspl_bp = Blueprint("tspl", __name__)


class TsplGenerateRequest(BaseModel):
    template_id: int | None = None
    canvas_data: dict[str, Any] | None = None
    dpi: int = 203


def _resolve_canvas(payload: TsplGenerateRequest) -> dict[str, Any] | None:
    if payload.canvas_data is not None:
        return payload.canvas_data
    if payload.template_id is None:
        return None
    session = get_session()
    tpl = tpl_svc.get(session, payload.template_id, requesting_user_id=current_user.id)
    return dict(tpl.canvas_data) if tpl.canvas_data else {}


def _resolve_template_name(template_id: int) -> str | None:
    session = get_session()
    try:
        tpl = tpl_svc.get(session, template_id, requesting_user_id=current_user.id)
    except (tpl_svc.TemplateNotFoundError, tpl_svc.TemplateAccessError):
        return None
    return _safe_filename(tpl.name)


@tspl_bp.post("/tspl/generate")
@login_required
def generate_endpoint() -> ResponseReturnValue:
    try:
        payload = TsplGenerateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    try:
        canvas_data = _resolve_canvas(payload)
    except tpl_svc.TemplateNotFoundError:
        return jsonify({"error": "template_not_found"}), 404
    except tpl_svc.TemplateAccessError:
        return jsonify({"error": "forbidden"}), 403
    if canvas_data is None:
        return jsonify({"error": "no_canvas", "detail": "provide canvas_data or template_id"}), 400

    canvas_data = substitute_dates_in_canvas(canvas_data)
    warnings: list[dict[str, Any]] = []
    tspl_text = generate_tspl(canvas_data, dpmm=dpmm_for_dpi(payload.dpi), warnings=warnings)

    name = "labels"
    if payload.template_id is not None:
        name = _resolve_template_name(payload.template_id) or name

    response = Response(tspl_text, mimetype="text/plain; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{name}.txt"'
    response.headers["Cache-Control"] = "no-store"
    if warnings:
        response.headers["X-TSPL-Warnings"] = json.dumps(warnings)
        response.headers["Access-Control-Expose-Headers"] = "X-TSPL-Warnings"
    return response
