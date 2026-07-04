"""Template + label-format endpoints."""

from __future__ import annotations

import json
import re

from flask import Blueprint, Response, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import ValidationError
from sqlalchemy import select

from app.api_helpers import validation_error_response
from app.db.session import get_session
from app.models.label_format import LabelFormat
from app.schemas.template import (
    CreateTemplateRequest,
    ImportRequest,
    LabelFormatPublic,
    TemplateExport,
    TemplatePublic,
    TemplateSummary,
    UpdateTemplateRequest,
)
from app.services import templates as tpl_svc
from app.services import templates_io as tpl_io
from app.services.folders import FolderNotFoundError

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

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
    """List templates. `scope=mine` (default) → own only, optionally
    filtered by `folder_id=<id>` or `folder_id=none` (unfiled).
    `scope=library` → everything shared, with the owner's email."""
    session = get_session()
    scope = request.args.get("scope", "mine")
    if scope == "library":
        items = tpl_svc.list_library(session)
        out = []
        for t in items:
            row = TemplateSummary.model_validate(t).model_dump(mode="json")
            row["owner_email"] = t.owner.email
            out.append(row)
        return jsonify({"templates": out})

    folder_arg = request.args.get("folder_id")
    unfiled = folder_arg == "none"
    folder_id = int(folder_arg) if folder_arg and folder_arg.isdigit() else None
    items = tpl_svc.list_mine(
        session, owner_id=current_user.id, folder_id=folder_id, unfiled_only=unfiled
    )
    return jsonify(
        {"templates": [TemplateSummary.model_validate(t).model_dump(mode="json") for t in items]}
    )


@templates_bp.post("/templates/<int:template_id>/clone")
@login_required
def clone_template(template_id: int) -> ResponseReturnValue:
    """\"Użyj\" from the library: copy an accessible template (with its
    image assets) into the caller's own templates."""
    session = get_session()
    try:
        tpl = tpl_svc.clone(session, template_id, requesting_user_id=current_user.id)
    except tpl_svc.TemplateNotFoundError:
        return jsonify({"error": "template_not_found"}), 404
    except tpl_svc.TemplateAccessError:
        return jsonify({"error": "template_not_found"}), 404
    return jsonify(TemplatePublic.model_validate(tpl).model_dump(mode="json")), 201


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
            width_mm=payload.width_mm,
            height_mm=payload.height_mm,
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
            width_mm=payload.width_mm,
            height_mm=payload.height_mm,
            folder_id=payload.folder_id,
            folder_id_set="folder_id" in payload.model_fields_set,
        )
    except tpl_svc.TemplateNotFoundError:
        return jsonify({"error": "template_not_found"}), 404
    except tpl_svc.TemplateAccessError:
        return jsonify({"error": "forbidden"}), 403
    except FolderNotFoundError:
        return jsonify({"error": "folder_not_found"}), 400

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


@templates_bp.get("/templates/<int:template_id>/export")
@login_required
def export_template(template_id: int) -> ResponseReturnValue:
    """Download a Template as a self-contained `.blg-template.json` file."""
    session = get_session()
    try:
        payload = tpl_io.export_template(session, template_id, current_user)
    except tpl_io.TemplateExportError as exc:
        msg = str(exc)
        if "not found" in msg:
            return jsonify({"error": "template_not_found"}), 404
        if "not accessible" in msg:
            return jsonify({"error": "forbidden"}), 403
        return jsonify({"error": "export_failed", "detail": msg}), 500

    safe = _SAFE_FILENAME_RE.sub("_", payload["template"]["name"]).strip("_") or "template"
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    response = Response(body, mimetype="application/json")
    response.headers["Content-Disposition"] = f'attachment; filename="{safe}.blg-template.json"'
    response.headers["Cache-Control"] = "no-store"
    return response


@templates_bp.post("/templates/import/preview")
@login_required
def preview_import_template() -> ResponseReturnValue:
    """Return a pre-flight summary of the uploaded file so the wizard can
    render object checkboxes + per-duplicate reuse/copy radios."""
    try:
        source = TemplateExport.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        preview = tpl_io.preview_import(session, source, current_user)
    except tpl_io.TemplateImportError as exc:
        return jsonify({"error": "import_rejected", "detail": str(exc)}), 400

    return jsonify(preview.model_dump(mode="json"))


@templates_bp.post("/templates/import")
@login_required
def import_template_endpoint() -> ResponseReturnValue:
    """Materialize an uploaded TemplateExport into a new Template + Assets."""
    try:
        payload = ImportRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    session = get_session()
    try:
        tpl = tpl_io.import_template(session, payload.source, payload.options, current_user)
    except tpl_io.TemplateImportError as exc:
        return jsonify({"error": "import_rejected", "detail": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": "import_failed", "detail": str(exc)}), 400

    return jsonify(TemplatePublic.model_validate(tpl).model_dump(mode="json")), 201
