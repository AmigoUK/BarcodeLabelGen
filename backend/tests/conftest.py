from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.config import Config
from app.factory import create_app


@pytest.fixture
def app() -> Flask:
    return create_app(
        Config(
            database_url="postgresql://invalid:invalid@127.0.0.1:1/invalid",
            redis_url="redis://127.0.0.1:1/0",
            flask_env="testing",
            secret_key="test-key",
        )
    )


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
