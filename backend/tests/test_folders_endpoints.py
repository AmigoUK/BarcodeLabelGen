"""HTTP tests for folders + template folder assignment + clone + starters."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.db.session import get_session
from app.services.users import create_user
from tests.conftest import CsrfHelper
from tests.test_templates_endpoints import _seed_format_and_login


def _mk_template(client: FlaskClient, csrf: CsrfHelper, fmt_id: int, name: str) -> int:
    resp = client.post(
        "/api/templates", json={"name": name, "format_id": fmt_id}, headers=csrf.headers()
    )
    return resp.get_json()["id"]


def _mk_folder(client: FlaskClient, csrf: CsrfHelper, name: str) -> int:
    resp = client.post("/api/folders", json={"name": name}, headers=csrf.headers())
    assert resp.status_code == 201
    return resp.get_json()["folder"]["id"]


def _login_second_user(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    client.post("/api/auth/logout", headers=csrf.headers())
    with app.app_context():
        create_user(get_session(), email="second@example.com", plain_password="secondPass123")
    client.post(
        "/api/auth/login",
        json={"email": "second@example.com", "password": "secondPass123"},
        headers=csrf.headers(),
    )


def test_folder_crud_and_counts(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    folder_id = _mk_folder(client, csrf, "Produkcja")
    tid = _mk_template(client, csrf, fmt_id, "W folderze")
    _mk_template(client, csrf, fmt_id, "Luzem")

    # move into folder via PUT
    assert (
        client.put(
            f"/api/templates/{tid}", json={"folder_id": folder_id}, headers=csrf.headers()
        ).status_code
        == 200
    )
    folders = client.get("/api/folders").get_json()["folders"]
    assert folders == [
        {
            "id": folder_id,
            "name": "Produkcja",
            "color": None,
            "template_count": 1,
            "created_at": folders[0]["created_at"],
        }
    ]

    # filtered listings
    in_folder = client.get(f"/api/templates?folder_id={folder_id}").get_json()["templates"]
    assert [t["id"] for t in in_folder] == [tid]
    unfiled = client.get("/api/templates?folder_id=none").get_json()["templates"]
    assert all(t["id"] != tid for t in unfiled) and len(unfiled) == 1

    # rename + duplicate-name conflict
    assert (
        client.patch(
            f"/api/folders/{folder_id}", json={"name": "Magazyn"}, headers=csrf.headers()
        ).status_code
        == 200
    )
    other = _mk_folder(client, csrf, "Inny")
    assert (
        client.patch(
            f"/api/folders/{other}", json={"name": "Magazyn"}, headers=csrf.headers()
        ).status_code
        == 409
    )

    # delete folder → template survives, unfiled
    assert client.delete(f"/api/folders/{folder_id}", headers=csrf.headers()).status_code == 204
    tpl = client.get(f"/api/templates/{tid}").get_json()
    assert tpl["folder_id"] is None


def test_folder_isolation_between_users(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    folder_id = _mk_folder(client, csrf, "Prywatny")
    tid = _mk_template(client, csrf, fmt_id, "Mój")

    _login_second_user(app, client, csrf)
    # can't see, rename, delete or assign into someone else's folder
    assert client.get("/api/folders").get_json()["folders"] == []
    assert (
        client.patch(
            f"/api/folders/{folder_id}", json={"name": "x"}, headers=csrf.headers()
        ).status_code
        == 404
    )
    assert client.delete(f"/api/folders/{folder_id}", headers=csrf.headers()).status_code == 404
    my_tid = _mk_template(client, csrf, fmt_id, "Cudzy folder")
    resp = client.put(
        f"/api/templates/{my_tid}", json={"folder_id": folder_id}, headers=csrf.headers()
    )
    assert resp.status_code == 400
    # and the other user's template is invisible in scope=mine
    mine = client.get("/api/templates").get_json()["templates"]
    assert all(t["id"] != tid for t in mine)


def test_clone_shared_template(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _mk_template(client, csrf, fmt_id, "Wzorzec")
    client.put(f"/api/templates/{tid}", json={"is_shared": True}, headers=csrf.headers())
    private_tid = _mk_template(client, csrf, fmt_id, "Prywatny wzorzec")

    _login_second_user(app, client, csrf)
    cloned = client.post(f"/api/templates/{tid}/clone", headers=csrf.headers())
    assert cloned.status_code == 201
    body = cloned.get_json()
    assert body["name"] == "Wzorzec (kopia)"
    assert body["is_shared"] is False
    # clone is mine — editable
    assert (
        client.put(
            f"/api/templates/{body['id']}", json={"name": "Moja wersja"}, headers=csrf.headers()
        ).status_code
        == 200
    )
    # someone else's private template can't be cloned
    assert (
        client.post(f"/api/templates/{private_tid}/clone", headers=csrf.headers()).status_code
        == 404
    )


def test_starters_list_and_use(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _seed_format_and_login(app, client, csrf)
    # Starter import falls back to the system Custom format (migration 0004
    # seeds it in real deployments; tests build schema from metadata).
    with app.app_context():
        from app.models.label_format import FormatKind, LabelFormat

        sess = get_session()
        sess.add(
            LabelFormat(
                name="Custom (define size)", width_mm=100, height_mm=100, kind=FormatKind.CUSTOM
            )
        )
        sess.commit()
    starters = client.get("/api/library/starters").get_json()["starters"]
    assert len(starters) >= 6
    slugs = {s["slug"] for s in starters}
    assert "01-etykieta-produktu" in slugs
    assert all(s["name"] and s["width_mm"] > 0 for s in starters)

    used = client.post("/api/library/starters/01-etykieta-produktu/use", headers=csrf.headers())
    assert used.status_code == 201
    body = used.get_json()
    assert body["width_mm"] == 50
    assert any(o.get("text") == "{{name}}" for o in body["canvas_data"]["objects"])
    # lands in my templates
    mine = client.get("/api/templates").get_json()["templates"]
    assert any(t["id"] == body["id"] for t in mine)

    assert (
        client.post("/api/library/starters/nope/use", headers=csrf.headers()).status_code == 404
    )


def test_folder_color(app: Flask, client: FlaskClient, csrf: CsrfHelper) -> None:
    _seed_format_and_login(app, client, csrf)
    resp = client.post(
        "/api/folders", json={"name": "Kolorowy", "color": "#e11d48"}, headers=csrf.headers()
    )
    assert resp.status_code == 201
    fid = resp.get_json()["folder"]["id"]
    assert resp.get_json()["folder"]["color"] == "#e11d48"

    # patch color only (name untouched), then clear it with explicit null
    patched = client.patch(
        f"/api/folders/{fid}", json={"color": "#2563eb"}, headers=csrf.headers()
    ).get_json()["folder"]
    assert patched == {**patched, "name": "Kolorowy", "color": "#2563eb"}
    cleared = client.patch(
        f"/api/folders/{fid}", json={"color": None}, headers=csrf.headers()
    ).get_json()["folder"]
    assert cleared["color"] is None

    # invalid color rejected
    assert (
        client.post(
            "/api/folders", json={"name": "Zly", "color": "red"}, headers=csrf.headers()
        ).status_code
        == 400
    )


def _upload_png(client: FlaskClient, csrf: CsrfHelper) -> int:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
    buf.seek(0)
    resp = client.post(
        "/api/assets/images",
        data={"file": (buf, "thumb.png", "image/png")},
        headers=csrf.headers(),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    return body.get("id") or body.get("asset", {}).get("id")


def test_featured_image_set_view_and_clone(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("ASSETS_DIR", str(tmp_path))
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _mk_template(client, csrf, fmt_id, "Z grafiką")
    asset_id = _upload_png(client, csrf)

    # set featured image
    assert (
        client.put(
            f"/api/templates/{tid}", json={"featured_asset_id": asset_id}, headers=csrf.headers()
        ).status_code
        == 200
    )
    img = client.get(f"/api/templates/{tid}/featured-image")
    assert img.status_code == 200
    assert img.mimetype == "image/png"

    # someone else's asset can't be attached; share + second user can view + clone
    client.put(f"/api/templates/{tid}", json={"is_shared": True}, headers=csrf.headers())
    _login_second_user(app, client, csrf)
    my_tid = _mk_template(client, csrf, fmt_id, "Cudzy asset")
    assert (
        client.put(
            f"/api/templates/{my_tid}",
            json={"featured_asset_id": asset_id},
            headers=csrf.headers(),
        ).status_code
        == 400
    )
    # viewer reads the shared template's thumbnail through the template route
    assert client.get(f"/api/templates/{tid}/featured-image").status_code == 200
    # clone copies the featured image into the cloner's account
    cloned = client.post(f"/api/templates/{tid}/clone", headers=csrf.headers()).get_json()
    assert cloned["featured_asset_id"] is not None
    assert cloned["featured_asset_id"] != asset_id
    assert client.get(f"/api/templates/{cloned['id']}/featured-image").status_code == 200


def test_featured_image_unset(
    app: Flask, client: FlaskClient, csrf: CsrfHelper, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("ASSETS_DIR", str(tmp_path))
    fmt_id = _seed_format_and_login(app, client, csrf)
    tid = _mk_template(client, csrf, fmt_id, "Bez grafiki")
    asset_id = _upload_png(client, csrf)
    client.put(
        f"/api/templates/{tid}", json={"featured_asset_id": asset_id}, headers=csrf.headers()
    )
    client.put(f"/api/templates/{tid}", json={"featured_asset_id": None}, headers=csrf.headers())
    assert client.get(f"/api/templates/{tid}/featured-image").status_code == 404
