"""Generated-file history endpoints (session auth, owner-only) — F18."""

from __future__ import annotations

from flask import Blueprint, jsonify, send_file
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required

from app.db.session import get_session
from app.services import generated_files as gf_svc
from app.services.jobs import pdfs_dir

history_bp = Blueprint("history", __name__)


@history_bp.get("/history")
@login_required
def list_history() -> ResponseReturnValue:
    session = get_session()
    entries = gf_svc.list_for_user(session, user_id=current_user.id)
    return jsonify(
        {
            "files": [
                {
                    "id": e.id,
                    "template_name": e.template_name,
                    "kind": e.kind,
                    "mode": e.mode,
                    "row_count": e.row_count,
                    "size_bytes": e.size_bytes,
                    "created_at": e.created_at.isoformat(),
                }
                for e in entries
            ]
        }
    )


@history_bp.get("/history/<int:file_id>/download")
@login_required
def download_history(file_id: int) -> ResponseReturnValue:
    session = get_session()
    row = gf_svc.get_for_user(session, file_id, user_id=current_user.id)
    if row is None:
        return jsonify({"error": "not_found"}), 404
    path = pdfs_dir() / row.storage_filename
    if not path.is_file():
        return jsonify({"error": "file_missing"}), 410
    mimetype = "text/plain; charset=utf-8" if row.kind == "zpl" else "application/pdf"
    ext = "zpl" if row.kind == "zpl" else "pdf"
    safe = row.template_name.encode("ascii", "ignore").decode() or "labels"
    download_name = f"{safe}.{ext}".replace(" ", "_")
    return send_file(path, mimetype=mimetype, as_attachment=True, download_name=download_name)


@history_bp.delete("/history/<int:file_id>")
@login_required
def delete_history(file_id: int) -> ResponseReturnValue:
    session = get_session()
    if not gf_svc.delete(session, file_id, user_id=current_user.id):
        return jsonify({"error": "not_found"}), 404
    return "", 204
