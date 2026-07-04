"""Starter-template library (F31).

Starters are ordinary `.blg-template.json` exports bundled with the app in
`app/library/` — versioned in git, validated and materialized through the
existing template-import machinery, so there is no seed data and no system
user.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required
from pydantic import ValidationError

from app.db.session import get_session
from app.schemas.template import ImportOptions, TemplateExport, TemplatePublic
from app.services import templates_io as tpl_io

library_bp = Blueprint("library", __name__)

LIBRARY_DIR = Path(__file__).resolve().parent.parent / "library"


@lru_cache(maxsize=1)
def _starters() -> dict[str, TemplateExport]:
    """slug → parsed starter, loaded once per process. A malformed bundled
    file is a packaging bug — fail loudly at first access, not per request."""
    out: dict[str, TemplateExport] = {}
    for path in sorted(LIBRARY_DIR.glob("*.json")):
        try:
            out[path.stem] = TemplateExport.model_validate(json.loads(path.read_text("utf-8")))
        except (ValidationError, json.JSONDecodeError) as exc:  # pragma: no cover
            raise RuntimeError(f"invalid bundled starter {path.name}: {exc}") from exc
    return out


@library_bp.get("/library/starters")
@login_required
def list_starters() -> ResponseReturnValue:
    starters = [
        {
            "slug": slug,
            "name": src.template.name,
            "description": src.template.description,
            "width_mm": src.template.width_mm,
            "height_mm": src.template.height_mm,
        }
        for slug, src in _starters().items()
    ]
    return jsonify({"starters": starters})


@library_bp.post("/library/starters/<slug>/use")
@login_required
def use_starter(slug: str) -> ResponseReturnValue:
    source = _starters().get(slug)
    if source is None:
        return jsonify({"error": "starter_not_found"}), 404
    session = get_session()
    tpl = tpl_io.import_template(session, source, ImportOptions(), current_user)
    return jsonify(TemplatePublic.model_validate(tpl).model_dump(mode="json")), 201
