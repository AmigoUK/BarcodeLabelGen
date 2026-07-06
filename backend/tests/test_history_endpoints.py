"""Generated-file history (F18): single/batch recording, retention, download."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.models.user import Role
from app.services.users import create_user
from tests.conftest import CsrfHelper
from tests.test_templates_endpoints import _seed_format_and_login

_CANVAS = {
    "version": 1,
    "stage": {"width_mm": 50, "height_mm": 30},
    "objects": [{"id": "t", "type": "text", "x": 2, "y": 2, "text": "hello", "fontSize": 5}],
}


def _template(client: FlaskClient, csrf: CsrfHelper, fmt_id: int) -> int:
    return client.post(
        "/api/templates",
        json={"name": "Historia", "format_id": fmt_id, "canvas_data": _CANVAS},
        headers=csrf.headers(),
    ).get_json()["id"]


def test_single_pdf_recorded_in_history(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("PDFS_DIR", str(tmp_path))
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _template(client, csrf, fmt_id)

    resp = client.post("/api/generate", json={"template_id": tid}, headers=csrf.headers())
    assert resp.status_code == 200
    assert resp.data.startswith(b"%PDF-")

    files = client.get("/api/history").get_json()["files"]
    assert len(files) == 1
    entry = files[0]
    assert entry["kind"] == "pdf" and entry["mode"] == "single"
    assert entry["template_name"] == "Historia"
    assert entry["size_bytes"] > 0

    # re-download returns the same PDF
    dl = client.get(f"/api/history/{entry['id']}/download")
    assert dl.status_code == 200
    assert dl.data.startswith(b"%PDF-")
    assert dl.mimetype == "application/pdf"


def test_history_hides_entry_without_file(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path, monkeypatch
) -> None:
    """A batch entry is recorded up-front but must not appear until the file
    (written by the worker thread) exists."""
    monkeypatch.setenv("PDFS_DIR", str(tmp_path))
    _seed_format_and_login(app, client, csrf)
    owner_id = client.get("/api/me").get_json()["id"]
    with app.app_context():
        from app.services import generated_files as gf_svc

        gf_svc.record(
            get_session(),
            owner_id=owner_id,
            template_id=None,
            template_name="Pending batch",
            kind="pdf",
            mode="series",
            storage_filename="does-not-exist.pdf",
            row_count=100,
        )
    assert client.get("/api/history").get_json()["files"] == []


def test_retention_drops_old_entries(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("PDFS_DIR", str(tmp_path))
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _template(client, csrf, fmt_id)
    client.post("/api/generate", json={"template_id": tid}, headers=csrf.headers())

    # Age the existing row past 30 days, then a new record() must prune it.
    with app.app_context():
        from app.models.generated_file import GeneratedFile
        from app.services import generated_files as gf_svc

        sess = get_session()
        row = sess.query(GeneratedFile).first()
        assert row is not None
        old_name = row.storage_filename
        row.created_at = datetime.now(UTC) - timedelta(days=31)
        sess.commit()
        gf_svc.record(
            sess,
            owner_id=row.owner_id,
            template_id=None,
            template_name="fresh",
            kind="pdf",
            mode="single",
            storage_filename="fresh.pdf",
        )
        remaining = {r.storage_filename for r in sess.query(GeneratedFile).all()}
        assert old_name not in remaining
        assert not (tmp_path / old_name).exists()  # file pruned too


def test_history_owner_scoped_and_delete(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("PDFS_DIR", str(tmp_path))
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _template(client, csrf, fmt_id)
    client.post("/api/generate", json={"template_id": tid}, headers=csrf.headers())
    fid = client.get("/api/history").get_json()["files"][0]["id"]

    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        create_user(get_session(), email="other@example.com", plain_password="pw", role=Role.EDITOR)
    client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "pw"},
        headers=csrf.headers(),
    )
    assert client.get("/api/history").get_json()["files"] == []
    assert client.get(f"/api/history/{fid}/download").status_code == 404
    assert client.delete(f"/api/history/{fid}", headers=csrf.headers()).status_code == 404


def test_delete_removes_file(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("PDFS_DIR", str(tmp_path))
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _template(client, csrf, fmt_id)
    client.post("/api/generate", json={"template_id": tid}, headers=csrf.headers())
    fid = client.get("/api/history").get_json()["files"][0]["id"]
    files_before = list(tmp_path.iterdir())
    assert files_before

    assert client.delete(f"/api/history/{fid}", headers=csrf.headers()).status_code == 204
    assert client.get("/api/history").get_json()["files"] == []
    assert list(tmp_path.iterdir()) == []
