"""Integration tests for template export/import (.blg-template.json).

These tests run through the Flask test client so they exercise the full
route → service → DB pipeline. Asset binaries are tiny PNGs created on
the fly with PIL — the round-trip checks that bytes survive the
base64 + sha256 + on-disk-rewrite path intact.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from PIL import Image

from app.db.session import get_session
from app.models.label_format import FormatKind, LabelFormat
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper


@pytest.fixture(autouse=True)
def _isolate_assets_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSETS_DIR", str(tmp_path / "assets"))


def _seed_formats(app: Flask) -> int:
    """Seed an A6 format + the "Custom (define size)" fallback (the latter
    is normally seeded by Alembic migration 0004, which the in-memory test
    DB doesn't run). Returns the A6 format id."""
    with app.app_context():
        sess = get_session()
        a6 = LabelFormat(name="A6", width_mm=105, height_mm=148, kind=FormatKind.A_PAPER)
        custom = LabelFormat(
            name="Custom (define size)",
            width_mm=100,
            height_mm=100,
            kind=FormatKind.CUSTOM,
            is_system=True,
        )
        sess.add_all([a6, custom])
        sess.commit()
        return a6.id


def _login(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, *, email: str = "u@example.com"
) -> None:
    with app.app_context():
        create_user(get_session(), email=email, plain_password="password123!", role=Role.EDITOR)
    client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123!"},
        headers=csrf.headers(),
    )


def _png_bytes(color: tuple[int, int, int, int] = (255, 0, 0, 255)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (10, 10), color).save(buf, format="PNG")
    return buf.getvalue()


def _create_template(
    client: FlaskClient,
    csrf: CsrfHelper,
    *,
    format_id: int,
    canvas: dict[str, Any],
    name: str = "Tpl",
) -> int:
    response = client.post(
        "/api/templates",
        json={"name": name, "format_id": format_id, "canvas_data": canvas},
        headers=csrf.headers(),
    )
    assert response.status_code == 201, response.get_json()
    return int(response.get_json()["id"])


def _upload_asset(client: FlaskClient, csrf: CsrfHelper, *, raw: bytes) -> int:
    response = client.post(
        "/api/assets/images",
        data={"file": (io.BytesIO(raw), "logo.png")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 201, response.get_json()
    return int(response.get_json()["id"])


def _basic_canvas(width_mm: float = 105, height_mm: float = 148) -> dict[str, Any]:
    return {
        "version": 1,
        "stage": {"width_mm": width_mm, "height_mm": height_mm},
        "objects": [
            {
                "id": "txt_1",
                "type": "text",
                "x": 10,
                "y": 12,
                "text": "{{name}}",
                "fontSize": 8,
                "fontFamily": "Helvetica",
                "fill": "#000",
            },
            {
                "id": "bar_1",
                "type": "barcode",
                "x": 10,
                "y": 30,
                "width": 50,
                "height": 15,
                "barcodeType": "code128",
                "data": "{{sku}}",
            },
        ],
    }


# ---------------- export ----------------


def test_export_template_returns_attachment_json(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=_basic_canvas())

    response = client.get(f"/api/templates/{tpl_id}/export")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert ".blg-template.json" in (response.headers.get("Content-Disposition") or "")

    payload = json.loads(response.data)
    assert payload["$schema"] == "blg-template/v1"
    assert payload["template"]["name"] == "Tpl"
    assert payload["template"]["width_mm"] == 105
    assert payload["template"]["format_hint"]["name"] == "A6"
    assert payload["canvas_data"]["objects"][0]["id"] == "txt_1"
    assert payload["assets"] == []  # no image objects


def test_export_template_bundles_image_assets(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    asset_id = _upload_asset(client, csrf, raw=_png_bytes())

    canvas = _basic_canvas()
    canvas["objects"].append(
        {
            "id": "img_1",
            "type": "image",
            "x": 0,
            "y": 0,
            "width": 30,
            "height": 20,
            "assetId": asset_id,
        }
    )
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=canvas)

    response = client.get(f"/api/templates/{tpl_id}/export")
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert len(payload["assets"]) == 1
    asset = payload["assets"][0]
    assert asset["mime_type"] == "image/png"
    assert len(asset["sha256"]) == 64
    assert asset["data_b64"]
    # The image object in canvas_data now uses assetRef, not assetId.
    img_obj = next(o for o in payload["canvas_data"]["objects"] if o["type"] == "image")
    assert "assetId" not in img_obj
    assert img_obj["assetRef"] == asset["ref"]


def test_export_owner_guard(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=_basic_canvas())

    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        create_user(
            get_session(),
            email="other@example.com",
            plain_password="otherPass123",
            role=Role.EDITOR,
        )
    client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "otherPass123"},
        headers=csrf.headers(),
    )
    assert client.get(f"/api/templates/{tpl_id}/export").status_code == 403


# ---------------- preview ----------------


def test_preview_import_reports_objects_and_no_duplicates(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=_basic_canvas())
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)

    # Log out + sign in as a fresh user so duplicates are guaranteed not to
    # exist on this user's side.
    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        create_user(
            get_session(),
            email="fresh@example.com",
            plain_password="freshPass123",
            role=Role.EDITOR,
        )
    client.post(
        "/api/auth/login",
        json={"email": "fresh@example.com", "password": "freshPass123"},
        headers=csrf.headers(),
    )

    preview = client.post("/api/templates/import/preview", json=source, headers=csrf.headers())
    assert preview.status_code == 200
    body = preview.get_json()
    assert body["template_name"] == "Tpl"
    assert body["width_mm"] == 105
    assert {o["id"] for o in body["object_summary"]} == {"txt_1", "bar_1"}
    assert body["asset_duplicates"] == []
    # Format "A6" only exists for the original user's instance scope, but
    # LabelFormat is global → it matches and there are no warnings.
    assert body["warnings"] == []


def test_preview_import_flags_duplicate_assets(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    asset_id = _upload_asset(client, csrf, raw=_png_bytes())
    canvas = _basic_canvas()
    canvas["objects"].append(
        {
            "id": "img_1",
            "type": "image",
            "x": 0,
            "y": 0,
            "width": 30,
            "height": 20,
            "assetId": asset_id,
        }
    )
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=canvas)
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)

    # Same user importing back — the asset is byte-identical to one they own.
    preview = client.post("/api/templates/import/preview", json=source, headers=csrf.headers())
    assert preview.status_code == 200
    dups = preview.get_json()["asset_duplicates"]
    assert len(dups) == 1
    assert dups[0]["matches_existing"] is True
    assert dups[0]["existing_asset_id"] == asset_id


def test_preview_rejects_unknown_schema_version(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    _seed_formats(app)
    response = client.post(
        "/api/templates/import/preview",
        json={
            "$schema": "blg-template/v999",
            "exportedAt": "2026-05-13T12:00:00Z",
            "template": {"name": "x", "width_mm": 50, "height_mm": 30},
            "canvas_data": {"version": 1, "stage": {}, "objects": []},
        },
        headers=csrf.headers(),
    )
    assert response.status_code == 400


# ---------------- import ----------------


def test_import_roundtrip_no_images(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=_basic_canvas())
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)

    response = client.post(
        "/api/templates/import",
        json={"source": source, "options": {}},
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    imported = response.get_json()
    assert imported["name"] == "Tpl (kopia)"  # original name taken → suffix
    assert imported["width_mm"] == 105
    assert {o["id"] for o in imported["canvas_data"]["objects"]} == {"txt_1", "bar_1"}


def test_import_with_image_reuse_existing(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    asset_id = _upload_asset(client, csrf, raw=_png_bytes())
    canvas = _basic_canvas()
    canvas["objects"].append(
        {
            "id": "img_1",
            "type": "image",
            "x": 0,
            "y": 0,
            "width": 30,
            "height": 20,
            "assetId": asset_id,
        }
    )
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=canvas)
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)
    ref = source["assets"][0]["ref"]

    response = client.post(
        "/api/templates/import",
        json={
            "source": source,
            "options": {"asset_resolution": {ref: "reuse"}},
        },
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    imported = response.get_json()
    img_obj = next(o for o in imported["canvas_data"]["objects"] if o["type"] == "image")
    # Same FK → same Asset row reused, no duplicate on disk.
    assert img_obj["assetId"] == asset_id


def test_import_with_image_create_new(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    asset_id = _upload_asset(client, csrf, raw=_png_bytes())
    canvas = _basic_canvas()
    canvas["objects"].append(
        {
            "id": "img_1",
            "type": "image",
            "x": 0,
            "y": 0,
            "width": 30,
            "height": 20,
            "assetId": asset_id,
        }
    )
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=canvas)
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)
    ref = source["assets"][0]["ref"]

    response = client.post(
        "/api/templates/import",
        json={
            "source": source,
            "options": {"asset_resolution": {ref: "new"}},
        },
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    imported = response.get_json()
    img_obj = next(o for o in imported["canvas_data"]["objects"] if o["type"] == "image")
    # Different Asset row but same hash — both rows survive.
    assert img_obj["assetId"] != asset_id


def test_import_size_override(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=_basic_canvas())
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)

    response = client.post(
        "/api/templates/import",
        json={
            "source": source,
            "options": {"width_mm": 80, "height_mm": 50, "name": "Resized"},
        },
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    imported = response.get_json()
    assert imported["name"] == "Resized"
    assert imported["width_mm"] == 80
    assert imported["height_mm"] == 50
    assert imported["canvas_data"]["stage"]["width_mm"] == 80


def test_import_skip_object_ids(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=_basic_canvas())
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)

    response = client.post(
        "/api/templates/import",
        json={"source": source, "options": {"skip_object_ids": ["bar_1"]}},
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    imported = response.get_json()
    ids = {o["id"] for o in imported["canvas_data"]["objects"]}
    assert ids == {"txt_1"}


def test_import_skip_image_means_asset_not_created(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    """If an image object is skipped, no new Asset should land in the user's library."""
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    asset_id = _upload_asset(client, csrf, raw=_png_bytes((0, 255, 0, 255)))
    canvas = _basic_canvas()
    canvas["objects"].append(
        {
            "id": "img_1",
            "type": "image",
            "x": 0,
            "y": 0,
            "width": 30,
            "height": 20,
            "assetId": asset_id,
        }
    )
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=canvas)
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)

    before = client.get("/api/assets/images").get_json()
    before_count = len(before["assets"])

    response = client.post(
        "/api/templates/import",
        json={"source": source, "options": {"skip_object_ids": ["img_1"]}},
        headers=csrf.headers(),
    )
    assert response.status_code == 201

    after = client.get("/api/assets/images").get_json()
    assert len(after["assets"]) == before_count  # no new Asset


def test_import_rejects_unknown_skip_id(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=_basic_canvas())
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)

    response = client.post(
        "/api/templates/import",
        json={"source": source, "options": {"skip_object_ids": ["nonexistent"]}},
        headers=csrf.headers(),
    )
    assert response.status_code == 400


def test_import_rejects_tampered_sha(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    """If the bundled sha256 doesn't match the base64 contents, refuse."""
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    asset_id = _upload_asset(client, csrf, raw=_png_bytes())
    canvas = _basic_canvas()
    canvas["objects"].append(
        {
            "id": "img_1",
            "type": "image",
            "x": 0,
            "y": 0,
            "width": 30,
            "height": 20,
            "assetId": asset_id,
        }
    )
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=canvas)
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)

    # Tamper: change the base64 payload, leave sha256 as-is.
    fresh = base64.b64encode(_png_bytes((0, 0, 255, 255))).decode("ascii")
    source["assets"][0]["data_b64"] = fresh

    response = client.post(
        "/api/templates/import",
        json={
            "source": source,
            "options": {"asset_resolution": {source["assets"][0]["ref"]: "new"}},
        },
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert "sha256" in response.get_json()["detail"]


def test_import_cross_user_owns_new_template(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=_basic_canvas())
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)

    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        create_user(
            get_session(),
            email="other@example.com",
            plain_password="otherPass123",
            role=Role.EDITOR,
        )
    client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "otherPass123"},
        headers=csrf.headers(),
    )

    response = client.post(
        "/api/templates/import",
        json={"source": source, "options": {}},
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    me = client.get("/api/me").get_json()
    assert response.get_json()["owner_id"] == me["id"]


def test_import_warning_for_unknown_format(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    fmt_id = _seed_formats(app)
    tpl_id = _create_template(client, csrf, format_id=fmt_id, canvas=_basic_canvas())
    source = json.loads(client.get(f"/api/templates/{tpl_id}/export").data)
    source["template"]["format_hint"]["name"] = "PinkUnicorn"

    preview = client.post("/api/templates/import/preview", json=source, headers=csrf.headers())
    assert preview.status_code == 200
    assert any("PinkUnicorn" in w for w in preview.get_json()["warnings"])

    # Import still succeeds — falls back to Custom format.
    imp = client.post(
        "/api/templates/import",
        json={"source": source, "options": {}},
        headers=csrf.headers(),
    )
    assert imp.status_code == 201
