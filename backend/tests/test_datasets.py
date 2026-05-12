from __future__ import annotations

import io
import sqlite3
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


def _sqlite_bytes(tmp_path: Path) -> bytes:
    """Build a small SQLite file on disk + return its raw bytes for upload."""
    p = tmp_path / "src.db"
    conn = sqlite3.connect(p)
    conn.executescript(
        """
        CREATE TABLE products (sku TEXT, name TEXT, price REAL);
        INSERT INTO products VALUES ('A001', 'Apple',  1.50);
        INSERT INTO products VALUES ('A002', 'Banana', 0.75);
        INSERT INTO products VALUES ('A003', 'Cherry', 3.20);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, sku TEXT, qty INTEGER);
        INSERT INTO orders (sku, qty) VALUES ('A001', 5), ('A002', 2);
        """
    )
    conn.commit()
    conn.close()
    return p.read_bytes()


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


# ---------------- SQLite source ----------------


def test_upload_sqlite_returns_tables_list(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path: Path
) -> None:
    _login(app, client, csrf)
    response = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_sqlite_bytes(tmp_path)), "shop.db")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["source_type"] == "sqlite"
    assert body["file_format"] == "db"
    # Before PATCH-config, the snapshot is empty — the wizard fills it in.
    assert body["columns"] == []
    assert body["row_count"] == 0
    assert body["sqlite_table"] is None
    assert body["sqlite_query"] is None
    tables = {t["name"]: t for t in body["sqlite_tables"]}
    assert set(tables) == {"products", "orders"}
    assert tables["products"]["columns"] == ["sku", "name", "price"]
    assert tables["products"]["row_count"] == 3


def test_upload_rejects_non_sqlite_file_with_db_extension(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _login(app, client, csrf)
    response = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(b"random garbage that is not sqlite"), "fake.db")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "upload_rejected"


def test_sqlite_config_with_table_snapshots_schema(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path: Path
) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_sqlite_bytes(tmp_path)), "shop.db")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    response = client.patch(
        f"/api/datasets/{dsid}/sqlite-config",
        json={"table": "products"},
        headers=csrf.headers(),
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["sqlite_table"] == "products"
    assert body["sqlite_query"] is None
    assert body["columns"] == ["sku", "name", "price"]
    assert body["row_count"] == 3


def test_sqlite_config_with_custom_select(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path: Path
) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_sqlite_bytes(tmp_path)), "shop.db")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    response = client.patch(
        f"/api/datasets/{dsid}/sqlite-config",
        json={"query": "SELECT sku, UPPER(name) AS name FROM products WHERE price > 1"},
        headers=csrf.headers(),
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["sqlite_query"].startswith("SELECT sku, UPPER")
    assert body["columns"] == ["sku", "name"]
    assert body["row_count"] == 2


def test_sqlite_config_rejects_dangerous_query(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path: Path
) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_sqlite_bytes(tmp_path)), "shop.db")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    response = client.patch(
        f"/api/datasets/{dsid}/sqlite-config",
        json={"query": "DROP TABLE products"},
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "sqlite_config_rejected"


def test_sqlite_config_requires_exactly_one(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path: Path
) -> None:
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_sqlite_bytes(tmp_path)), "shop.db")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]

    # Both set → 400 (Pydantic xor)
    both = client.patch(
        f"/api/datasets/{dsid}/sqlite-config",
        json={"table": "products", "query": "SELECT 1"},
        headers=csrf.headers(),
    )
    assert both.status_code == 400

    # Neither set → 400 (Pydantic xor)
    neither = client.patch(
        f"/api/datasets/{dsid}/sqlite-config",
        json={},
        headers=csrf.headers(),
    )
    assert neither.status_code == 400


def test_sqlite_config_on_csv_dataset_is_400(
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

    response = client.patch(
        f"/api/datasets/{dsid}/sqlite-config",
        json={"table": "products"},
        headers=csrf.headers(),
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "not_a_sqlite_dataset"


def test_load_rows_dispatches_for_sqlite(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path: Path
) -> None:
    """End-to-end: after PATCH config, load_rows returns the expected dicts.

    Goes through the service rather than the route since /generate kicks
    off a background thread that needs Redis (which the test stack
    doesn't run).
    """
    from app.services import datasets as ds_svc

    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_sqlite_bytes(tmp_path)), "shop.db")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]
    client.patch(
        f"/api/datasets/{dsid}/sqlite-config",
        json={"table": "products"},
        headers=csrf.headers(),
    )

    with app.app_context():
        ds = ds_svc.get_dataset(get_session(), dsid)
        assert ds is not None
        rows = ds_svc.load_rows(ds)
        assert [r["sku"] for r in rows] == ["A001", "A002", "A003"]
        assert all(isinstance(v, str) for r in rows for v in r.values())


def test_filter_works_on_sqlite_dataset(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path: Path
) -> None:
    """The /filter endpoint is source-agnostic — it operates on load_rows output."""
    _login(app, client, csrf)
    upload = client.post(
        "/api/datasets",
        data={"file": (io.BytesIO(_sqlite_bytes(tmp_path)), "shop.db")},
        content_type="multipart/form-data",
        headers=csrf.headers(),
    )
    dsid = upload.get_json()["id"]
    client.patch(
        f"/api/datasets/{dsid}/sqlite-config",
        json={"table": "products"},
        headers=csrf.headers(),
    )

    response = client.post(
        f"/api/datasets/{dsid}/filter",
        json={"column": "price", "op": "gt", "value": "1.0"},
        headers=csrf.headers(),
    )
    assert response.status_code == 200
    assert response.get_json()["match_count"] == 2
