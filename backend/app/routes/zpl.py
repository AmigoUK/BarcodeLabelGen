"""ZPL/ZPL II round-trip endpoints.

  • POST /api/zpl/parse    — paste ZPL, get back a canvas_data tree to load
                             into the editor (+ soft warnings).
  • POST /api/zpl/generate — turn a canvas (the live editor state or a saved
                             template) into ZPL. Two modes:
      · template — returns text/plain ZPL synchronously, variables intact.
      · batch    — substitutes a dataset's {{column}} values per row and
                   returns 202 + job_id; the concatenated .zpl is polled
                   and downloaded through the shared /api/jobs endpoints.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal

from flask import Blueprint, Response, current_app, jsonify, request
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import BaseModel, Field, ValidationError

from app.api_helpers import validation_error_response
from app.config import Config
from app.db.session import get_session
from app.routes.generate import FilterSpec, _apply_mapping, _safe_filename
from app.services import datasets as ds_svc
from app.services import jobs as jobs_svc
from app.services import templates as tpl_svc
from app.services.placeholders import substitute_dates_in_canvas
from app.services.zpl import (
    InvalidZplError,
    detect_dpi,
    dpmm_for_dpi,
    generate_zpl,
    parse_zpl,
    validate_zpl,
)
from app.services.zpl.batch import render_batch_zpl

zpl_bp = Blueprint("zpl", __name__)

_MAX_ZPL_BYTES = 512 * 1024  # generous ceiling for a pasted label definition


class ZplParseRequest(BaseModel):
    zpl: str = Field(min_length=1, max_length=_MAX_ZPL_BYTES)
    # A concrete DPI, or "auto" to detect it from ^PW/^LL against the current
    # label size (passed as target_width_mm / target_height_mm).
    dpi: int | Literal["auto"] = 203
    target_width_mm: float | None = Field(default=None, gt=0, le=1000)
    target_height_mm: float | None = Field(default=None, gt=0, le=1000)


class ZplGenerateRequest(BaseModel):
    template_id: int | None = None
    canvas_data: dict[str, Any] | None = None
    dpi: int = 203
    mode: Literal["template", "batch"] = "template"
    dataset_id: int | None = None
    mapping: dict[str, str] | None = None
    filter: FilterSpec | None = None


@zpl_bp.post("/zpl/parse")
@login_required
def parse_endpoint() -> ResponseReturnValue:
    try:
        payload = ZplParseRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    try:
        validate_zpl(payload.zpl)
    except InvalidZplError as exc:
        return jsonify({"error": "invalid_zpl", "reason": exc.reason, "detail": exc.detail}), 422

    if payload.dpi == "auto":
        dpi = detect_dpi(
            payload.zpl,
            target_width_mm=payload.target_width_mm,
            target_height_mm=payload.target_height_mm,
        )
    else:
        dpi = int(payload.dpi)

    result = parse_zpl(payload.zpl, dpmm_for_dpi(dpi))
    result["detected_dpi"] = dpi
    return jsonify(result)


def _resolve_canvas(payload: ZplGenerateRequest) -> dict[str, Any] | None:
    """Live editor canvas wins; otherwise fall back to the saved template."""
    if payload.canvas_data is not None:
        return payload.canvas_data
    if payload.template_id is None:
        return None
    session = get_session()
    tpl = tpl_svc.get(session, payload.template_id, requesting_user_id=current_user.id)
    return dict(tpl.canvas_data) if tpl.canvas_data else {}


@zpl_bp.post("/zpl/generate")
@login_required
def generate_endpoint() -> ResponseReturnValue:
    try:
        payload = ZplGenerateRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return validation_error_response(exc)

    dpmm = dpmm_for_dpi(payload.dpi)

    # --- template / live-preview mode (sync) ------------------------------
    if payload.mode == "template":
        try:
            canvas_data = _resolve_canvas(payload)
        except tpl_svc.TemplateNotFoundError:
            return jsonify({"error": "template_not_found"}), 404
        except tpl_svc.TemplateAccessError:
            return jsonify({"error": "forbidden"}), 403
        if canvas_data is None:
            return jsonify(
                {"error": "no_canvas", "detail": "provide canvas_data or template_id"}
            ), 400

        # Resolve date placeholders now — no downstream ZPL consumer can
        # evaluate the app's {{...}} syntax. Printer variables in single
        # braces ({NAME}) pass through untouched.
        canvas_data = substitute_dates_in_canvas(canvas_data)
        warnings: list[dict[str, Any]] = []
        zpl_text = generate_zpl(canvas_data, dpmm=dpmm, warnings=warnings)
        name = "labels"
        if payload.template_id is not None:
            with_name = _resolve_template_name(payload.template_id)
            name = with_name or name
        response = Response(zpl_text, mimetype="text/plain; charset=utf-8")
        response.headers["Content-Disposition"] = f'attachment; filename="{name}.zpl"'
        response.headers["Cache-Control"] = "no-store"
        if warnings:
            response.headers["X-ZPL-Warnings"] = json.dumps(warnings)
            response.headers["Access-Control-Expose-Headers"] = "X-ZPL-Warnings"
        return response

    # --- batch mode (async job) -------------------------------------------
    if payload.template_id is None or payload.dataset_id is None:
        return jsonify({"error": "batch_requires_template_and_dataset"}), 400

    session = get_session()
    try:
        tpl = tpl_svc.get(session, payload.template_id, requesting_user_id=current_user.id)
    except tpl_svc.TemplateNotFoundError:
        return jsonify({"error": "template_not_found"}), 404
    except tpl_svc.TemplateAccessError:
        return jsonify({"error": "forbidden"}), 403

    ds = ds_svc.get_dataset(session, payload.dataset_id)
    if ds is None or ds.owner_id != current_user.id:
        return jsonify({"error": "dataset_not_found"}), 404

    rows = ds_svc.load_rows(ds)
    if payload.filter is not None:
        rows = ds_svc.apply_filter(
            rows, column=payload.filter.column, op=payload.filter.op, value=payload.filter.value
        )
    if not rows:
        return jsonify({"error": "no_rows", "detail": "filter matched no rows"}), 400

    projected = _apply_mapping(rows, payload.mapping)
    batch_canvas: dict[str, Any] = dict(tpl.canvas_data) if tpl.canvas_data else {}

    cfg: Config = current_app.config["APP_CONFIG"]
    job_id = jobs_svc.create_job(
        cfg.redis_url, owner_id=current_user.id, template_id=tpl.id, total=len(projected)
    )

    def _runner(
        progress_cb: Callable[[int, int], None], warnings: list[dict[str, Any]]
    ) -> bytes:
        return render_batch_zpl(
            batch_canvas, projected, dpmm=dpmm, on_progress=progress_cb, warnings=warnings
        )

    output_filename = f"{job_id}_{_safe_filename(tpl.name)}.zpl"
    from app.services import generated_files as gf_svc

    gf_svc.record(
        session,
        owner_id=current_user.id,
        template_id=tpl.id,
        template_name=tpl.name,
        kind="zpl",
        mode="series",
        storage_filename=output_filename,
        row_count=len(projected),
    )
    jobs_svc.run_in_thread(cfg.redis_url, job_id, runner=_runner, output_filename=output_filename)
    return jsonify({"job_id": job_id, "total": len(projected)}), 202


def _resolve_template_name(template_id: int) -> str | None:
    session = get_session()
    try:
        tpl = tpl_svc.get(session, template_id, requesting_user_id=current_user.id)
    except (tpl_svc.TemplateNotFoundError, tpl_svc.TemplateAccessError):
        return None
    return _safe_filename(tpl.name)
