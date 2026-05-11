"""Flask application factory."""

from __future__ import annotations

import logging

from flask import Flask

from app.config import Config
from app.routes.health import health_bp


def create_app(config: Config | None = None) -> Flask:
    app = Flask(__name__)
    app.config["APP_CONFIG"] = config or Config.from_env()
    app.config["SECRET_KEY"] = app.config["APP_CONFIG"].secret_key

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app.register_blueprint(health_bp, url_prefix="/api")

    return app
