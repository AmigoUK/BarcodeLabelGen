"""Shared pytest fixtures: in-memory SQLite + cookie sessions for fast tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.db.session as db_session_module
from app.auth.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.config import Config
from app.db.base import Base
from app.factory import create_app


@pytest.fixture(autouse=True)
def _pdfs_dir_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point PDFS_DIR at a per-test tmp dir so no test can touch the real
    volume — the default /app/pdfs doesn't exist on CI runners."""
    monkeypatch.setenv("PDFS_DIR", str(tmp_path / "pdfs"))


@pytest.fixture
def app() -> Iterator[Flask]:
    # SQLite in-memory shared across the test session via a single engine instance.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)

    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    flask_app = create_app(
        Config(
            database_url="sqlite:///:memory:",
            redis_url="redis://invalid:1/0",
            flask_env="testing",
            secret_key="test-key",
            cookie_secure=False,
        ),
        init_db=False,
        use_redis_sessions=False,
    )
    # Inject test engine + factory directly, bypassing init_engine
    db_session_module._engine = engine  # noqa: SLF001
    db_session_module._SessionFactory = test_session_factory  # noqa: SLF001

    yield flask_app

    Base.metadata.drop_all(engine)
    db_session_module._engine = None  # noqa: SLF001
    db_session_module._SessionFactory = None  # noqa: SLF001


@pytest.fixture
def db_session(app: Flask) -> Iterator[Session]:
    """Direct session for service-layer tests."""
    with app.app_context():
        sess = db_session_module.get_session()
        yield sess


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


class CsrfHelper:
    """Always-fresh CSRF header lookup that mirrors what a JS client does:

    read the current `csrf_token` cookie value at request time, since the
    server may rotate the cookie on login/logout.
    """

    def __init__(self, client: FlaskClient) -> None:
        self._client = client

    def headers(self) -> dict[str, str]:
        # Prime a cookie if none exists yet
        if self._client.get_cookie(CSRF_COOKIE_NAME) is None:
            self._client.get("/api/me")  # any non-exempt endpoint
        token = self._client.get_cookie(CSRF_COOKIE_NAME)
        assert token is not None, "CSRF cookie should have been set"
        return {CSRF_HEADER_NAME: token.value}


@pytest.fixture
def csrf(client: FlaskClient) -> CsrfHelper:
    return CsrfHelper(client)
