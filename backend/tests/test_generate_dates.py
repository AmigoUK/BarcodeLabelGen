"""Date placeholders resolve on the single-label PDF and template-ZPL paths."""

from __future__ import annotations

import re

from flask import Flask
from flask.testing import FlaskClient

from tests.conftest import CsrfHelper
from tests.test_templates_endpoints import _seed_format_and_login

_DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")

_CANVAS = {
    "objects": [
        {
            "id": "t1",
            "type": "text",
            "x": 5,
            "y": 5,
            "width": 80,
            "height": 10,
            "text": "EXP {{date+1d}} / {{operator}}",
            "fontSize": 4,
            "fontFamily": "Helvetica",
        }
    ]
}


def test_single_pdf_resolves_date_placeholder(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    tpl = client.post(
        "/api/templates",
        json={"name": "Dates", "format_id": fmt_id, "canvas_data": _CANVAS},
        headers=csrf.headers(),
    ).get_json()
    resp = client.post(
        "/api/generate", json={"template_id": tpl["id"]}, headers=csrf.headers()
    )
    assert resp.status_code == 200
    assert resp.data.startswith(b"%PDF-")


def test_template_zpl_resolves_date_but_keeps_columns(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _seed_format_and_login(app, client, csrf)
    resp = client.post(
        "/api/zpl/generate",
        json={"canvas_data": _CANVAS, "dpi": 203, "mode": "template"},
        headers=csrf.headers(),
    )
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert _DATE_RE.search(text), text
    assert "{{date" not in text
    # Column placeholders stay verbatim in template mode
    assert "{{operator}}" in text
