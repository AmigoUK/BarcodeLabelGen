"""Engine + scoped session lifecycle, bound to Flask app context."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import g
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from flask import Flask

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def init_engine(app: Flask, database_url: str) -> None:
    global _engine, _SessionFactory  # noqa: PLW0603
    _engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)

    @app.teardown_appcontext
    def _close_session_on_teardown(_exc: BaseException | None) -> None:
        close_session()


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("DB engine not initialized — call init_engine() first")
    return _engine


def get_session() -> Session:
    """Return the request-scoped SQLAlchemy session, creating it if needed."""
    if _SessionFactory is None:
        raise RuntimeError("DB session factory not initialized")
    if "db_session" not in g:
        g.db_session = _SessionFactory()
    return g.db_session  # type: ignore[no-any-return]


def close_session() -> None:
    sess: Session | None = g.pop("db_session", None)
    if sess is not None:
        sess.close()
