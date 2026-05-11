from __future__ import annotations

import io
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.services.users import create_user
from tests.conftest import CsrfHelper


@pytest.fixture(autouse=True)
def _isolate_uploads_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path / "uploads"))


def _login(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    with app.app_context():
        create_user(get_session(), email="u@example.com", plain_password="password123!")
    client.post(
        "/api/auth/login",
        json={"email": "u@example.com", "password": "password123!"},
        headers=csrf.headers(),
    )


def _csv_bytes() -> bytes:
    return b"sku,name,price\nA001,Apple,1.50\nA002,Banana,0.75\nA003,Cherry,3.20\n"


def test_upload_csv_returns_columns_and_row_count(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    response = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_csv_bytes()), "products.csv")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["original_filename"] == "products.csv"
    assert body["file_format"] == "csv"
    assert body["columns"] == ["sku", "name", "price"]
    assert body["row_count"] == 3


def test_upload_rejects_bad_extension(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    response = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(b"x"), "evil.exe")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "upload_rejected"


def test_upload_rejects_oversize(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    big = b"col\n" + (b"x\n" * 11_000_000)
    response = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(big), "x.csv")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 400


def test_upload_rejects_over_1000_rows(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    body = b"col\n" + b"\n".join(f"v{i}".encode() for i in range(1001)) + b"\n"
    response = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(body), "x.csv")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert "1000" in response.get_json()["detail"]


def test_preview_returns_first_n_rows(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_csv_bytes()), "p.csv")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    response = client.get(f"/api/datasets/{dsid}/preview?rows=2")
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 3
    assert len(body["rows"]) == 2
    assert body["rows"][0]["name"] == "Apple"


def test_filter_eq_matches_one_row(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_csv_bytes()), "p.csv")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    response = client.post(
        f"/api/datasets/{dsid}/filter",
        json={"column": "sku", "op": "eq", "value": "A002"},
        headers=csrf.headers(),
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["match_count"] == 1
    assert body["preview"][0]["name"] == "Banana"


def test_filter_gt_numeric(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_csv_bytes()), "p.csv")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    response = client.post(
        f"/api/datasets/{dsid}/filter",
        json={"column": "price", "op": "gt", "value": "1.0"},
        headers=csrf.headers(),
    )
    assert response.get_json()["match_count"] == 2


def test_filter_contains_case_insensitive(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_csv_bytes()), "p.csv")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    response = client.post(
        f"/api/datasets/{dsid}/filter",
        json={"column": "name", "op": "contains", "value": "AN"},
        headers=csrf.headers(),
    )
    assert response.get_json()["match_count"] == 1  # only "Banana"


def test_other_user_cannot_see_dataset(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_csv_bytes()), "p.csv")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        create_user(get_session(), email="other@example.com", plain_password="otherPass123")
    client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "otherPass123"},
        headers=csrf.headers(),
    )

    assert client.get(f"/api/datasets/{dsid}").status_code == 404
    assert client.get(f"/api/datasets/{dsid}/preview").status_code == 404


def test_delete_removes_dataset(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_csv_bytes()), "p.csv")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    assert client.delete(f"/api/datasets/{dsid}", headers=csrf.headers()).status_code == 204
    assert client.get(f"/api/datasets/{dsid}").status_code == 404
