"""PDF generation endpoints.

Two modes share the same /api/generate route:
  • Single label   — body has only template_id. Renders sync, returns
                     application/pdf inline.
  • Batch series   — body adds dataset_id + mapping (+ optional filter).
                     Returns 202 with a job_id; the heavy lifting runs
                     in a background thread and progress is polled via
                     /api/jobs/:id, with the finished PDF available at
                     /api/jobs/:id/download.

This shape lets the frontend use one POST and branch on response status,
without splitting the API surface.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request, send_file
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import BaseModel, Field, ValidationError

from app.api_helpers import validation_error_response
from app.config import Config
from app.db.session import get_session
from app.models.asset import Asset
from app.services import datasets as ds_svc
from app.services import jobs as jobs_svc
from app.services import templates as tpl_svc
from app.services.batch_render import AssetResolver, render_batch_pdf
from app.services.datasets import FilterOp
from app.services.pdf_renderer import PdfRenderError, render_template_pdf

generate_bp = Blueprint("generate", __name__)

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class FilterSpec(BaseModel):
    column: str = Field(min_length=1, max_length=255)
    op: FilterOp
    value: str = Field(default="", max_length=1000)


class GenerateRequest(BaseModel):
    template_id: int
    # Batch mode: pick a dataset; mapping {placeholder: column} is optional
    # — placeholders whose name matches a column auto-map.
    dataset_id: int | None = None
    mapping: dict[str, str] | None = None
    filter: FilterSpec | None = None


def _safe_filename(template_name: str) -> str:
    base = _SAFE_FILENAME.sub("_", template_name).strip("_")
    return base or "labels"


def _resolve_asset_factory() -> AssetResolver:
    session = get_session()
    is_admin = getattr(current_user, "is_admin", False)
    owner_id = current_user.id

    def _resolve(asset_id: int) -> Asset | None:
        asset = session.get(Asset, asset_id)
        if asset is None:
            return None
        if asset.owner_id != owner_id and not is_admin:
            return None
        return asset

    return _resolve


def _apply_mapping(
    rows: list[dict[str, str]], mapping: dict[str, str] | None
) -> list[dict[str, Any]]:
    """Project rows so placeholder names map to the right column values.

    Placeholders that already match a column name keep working without an
    explicit mapping entry — the mapping only needs entries for renames.
    """
    if not mapping:
        return list(rows)
    out: list[dict[str, Any]] = []
    for row in rows:
        projected = dict(row)
        for placeholder, column in mapping.items():
            if column in row:
                projected[placeholder] = row[column]
        out.append(projected)
    return out


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

    canvas_data: dict[str, Any] = dict(tpl.canvas_data) if tpl.canvas_data else {}

    # --- single-label sync mode -------------------------------------------
    if payload.dataset_id is None:
        try:
            pdf_bytes = render_template_pdf(
                canvas_data,
                width_mm=float(tpl.width_mm),
                height_mm=float(tpl.height_mm),
                resolve_asset=_resolve_asset_factory(),
            )
        except PdfRenderError as exc:
            return jsonify({"error": "pdf_render_failed", "detail": str(exc)}), 500

        filename = f"{_safe_filename(tpl.name)}.pdf"
        response = Response(pdf_bytes, mimetype="application/pdf")
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.headers["Cache-Control"] = "no-store"
        return response

    # --- batch async mode --------------------------------------------------
    ds = ds_svc.get_dataset(session, payload.dataset_id)
    if ds is None or ds.owner_id != current_user.id:
        return jsonify({"error": "dataset_not_found"}), 404

    rows = ds_svc.load_rows(ds)
    if payload.filter is not None:
        rows = ds_svc.apply_filter(
            rows,
            column=payload.filter.column,
            op=payload.filter.op,
            value=payload.filter.value,
        )
    if not rows:
        return jsonify({"error": "no_rows", "detail": "filter matched no rows"}), 400

    projected = _apply_mapping(rows, payload.mapping)

    cfg: Config = current_app.config["APP_CONFIG"]
    template_id = tpl.id
    template_name = tpl.name
    width_mm = float(tpl.width_mm)
    height_mm = float(tpl.height_mm)
    resolve_asset = _resolve_asset_factory()

    job_id = jobs_svc.create_job(
        cfg.redis_url,
        owner_id=current_user.id,
        template_id=template_id,
        total=len(projected),
    )

    def _runner(progress_cb: Callable[[int, int], None]) -> bytes:
        return render_batch_pdf(
            canvas_data,
            projected,
            width_mm=width_mm,
            height_mm=height_mm,
            resolve_asset=resolve_asset,
            on_progress=progress_cb,
        )

    output_filename = f"{job_id}_{_safe_filename(template_name)}.pdf"
    jobs_svc.run_in_thread(cfg.redis_url, job_id, runner=_runner, output_filename=output_filename)

    return jsonify({"job_id": job_id, "total": len(projected)}), 202


# --- job polling -----------------------------------------------------------


jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.get("/jobs/<job_id>")
@login_required
def get_job_status(job_id: str) -> ResponseReturnValue:
    cfg: Config = current_app.config["APP_CONFIG"]
    state = jobs_svc.get_job(cfg.redis_url, job_id)
    if state is None:
        return jsonify({"error": "job_not_found"}), 404
    if state["owner_id"] != current_user.id and not getattr(current_user, "is_admin", False):
        return jsonify({"error": "forbidden"}), 403
    # Don't leak the on-disk filename — the download URL is enough.
    public = {k: v for k, v in state.items() if k != "pdf_path"}
    return jsonify(public)


@jobs_bp.get("/jobs/<job_id>/download")
@login_required
def download_job_pdf(job_id: str) -> ResponseReturnValue:
    cfg: Config = current_app.config["APP_CONFIG"]
    state = jobs_svc.get_job(cfg.redis_url, job_id)
    if state is None:
        return jsonify({"error": "job_not_found"}), 404
    if state["owner_id"] != current_user.id and not getattr(current_user, "is_admin", False):
        return jsonify({"error": "forbidden"}), 403
    if state["status"] != jobs_svc.JobStatus.DONE.value:
        return jsonify({"error": "job_not_done", "status": state["status"]}), 409

    pdf_file = jobs_svc.pdfs_dir() / state["pdf_path"]
    if not pdf_file.is_file():
        return jsonify({"error": "pdf_missing"}), 410
    return send_file(
        pdf_file,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=pdf_file.name,
    )
