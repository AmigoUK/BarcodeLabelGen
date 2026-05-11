"""Template + label-format endpoints."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import ValidationError
from sqlalchemy import select

from app.api_helpers import validation_error_response
from app.db.session import get_session
from app.models.label_format import LabelFormat
from app.schemas.template import (
    CreateTemplateRequest,
    LabelFormatPublic,
    TemplatePublic,
    TemplateSummary,
    UpdateTemplateRequest,
)
from app.services import templates as tpl_svc

templates_bp = Blueprint("templates", __name__)


@templates_bp.get("/label-formats")
@login_required
def list_label_formats() -> ResponseReturnValue:
    session = get_session()
    formats = session.execute(
        select(LabelFormat).order_by(LabelFormat.is_system.desc(), LabelFormat.name)
    ).scalars()
    return jsonify(
        {"formats": [LabelFormatPublic.model_validate(f).model_dump(mode="json") for f in formats]}
    )


@templates_bp.get("/templates")
@login_required
def list_templates() -> ResponseReturnValue:
    session = get_session()
    items = tpl_svc.list_visible(session, owner_id=current_user.id)
    return jsonify(
        {"templates": [TemplateSummary.model_validate(t).model_dump(mode="json") for t in items]}
    )


@templates_bp.post("/templates")
@login_required
def create_template() -> ResponseReturnValue:
    try:
        payload = CreateTemplateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        tpl = tpl_svc.create(
            session,
            owner_id=current_user.id,
            name=payload.name,
            description=payload.description,
            format_id=payload.format_id,
            canvas_data=payload.canvas_data,
        )
    except ValueError as exc:
        return jsonify({"error": "invalid_format", "detail": str(exc)}), 400

    return jsonify(TemplatePublic.model_validate(tpl).model_dump(mode="json")), 201


@templates_bp.get("/templates/<int:template_id>")
@login_required
def get_template(template_id: int) -> ResponseReturnValue:
    session = get_session()
    try:
        tpl = tpl_svc.get(session, template_id, requesting_user_id=current_user.id)
    except tpl_svc.TemplateNotFoundError:
        return jsonify({"error": "template_not_found"}), 404
    except tpl_svc.TemplateAccessError:
        return jsonify({"error": "forbidden"}), 403
    return jsonify(TemplatePublic.model_validate(tpl).model_dump(mode="json"))


@templates_bp.put("/templates/<int:template_id>")
@login_required
def update_template(template_id: int) -> ResponseReturnValue:
    try:
        payload = UpdateTemplateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        tpl = tpl_svc.update(
            session,
            template_id,
            requesting_user_id=current_user.id,
            name=payload.name,
            description=payload.description,
            canvas_data=payload.canvas_data,
            is_shared=payload.is_shared,
        )
    except tpl_svc.TemplateNotFoundError:
        return jsonify({"error": "template_not_found"}), 404
    except tpl_svc.TemplateAccessError:
        return jsonify({"error": "forbidden"}), 403

    return jsonify(TemplatePublic.model_validate(tpl).model_dump(mode="json"))


@templates_bp.delete("/templates/<int:template_id>")
@login_required
def delete_template(template_id: int) -> ResponseReturnValue:
    session = get_session()
    try:
        tpl_svc.delete(session, template_id, requesting_user_id=current_user.id)
    except tpl_svc.TemplateNotFoundError:
        return jsonify({"error": "template_not_found"}), 404
    except tpl_svc.TemplateAccessError:
        return jsonify({"error": "forbidden"}), 403
    return "", 204
