"""Flask application factory."""

from __future__ import annotations

import logging

import redis
from flask import Flask

from app.auth.csrf import init_csrf
from app.cli.seed import register_cli
from app.config import Config
from app.db.session import get_session, init_engine
from app.extensions import login_manager, session_ext
from app.models.user import User
from app.routes.admin import admin_bp
from app.routes.assets import assets_bp
from app.routes.auth import auth_bp
from app.routes.barcodes import barcodes_bp
from app.routes.datasets import datasets_bp
from app.routes.generate import generate_bp, jobs_bp
from app.routes.health import health_bp
from app.routes.me import me_bp
from app.routes.templates import templates_bp


def create_app(
    config: Config | None = None,
    *,
    init_db: bool = True,
    use_redis_sessions: bool = True,
) -> Flask:
    app = Flask(__name__)
    cfg = config or Config.from_env()
    app.config["APP_CONFIG"] = cfg
    app.config["SECRET_KEY"] = cfg.secret_key

    # Cookie + session hardening (relaxed when not on HTTPS)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cfg.flask_env == "production" and cfg.cookie_secure,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,  # 8h sliding
    )
    if use_redis_sessions:
        app.config.update(
            SESSION_TYPE="redis",
            SESSION_REDIS=redis.Redis.from_url(cfg.redis_url),
            SESSION_PERMANENT=True,
            SESSION_USE_SIGNER=True,
            SESSION_KEY_PREFIX="blg:sess:",
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if init_db:
        init_engine(app, cfg.database_url)

    # Extensions
    if use_redis_sessions:
        session_ext.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = None  # API: return 401 instead of redirecting
    init_csrf(app)

    @login_manager.user_loader
    def _load_user(user_id: str) -> User | None:
        try:
            uid = int(user_id)
        except ValueError:
            return None
        return get_session().get(User, uid)

    @login_manager.unauthorized_handler
    def _unauthorized() -> tuple[dict[str, str], int]:
        return {"error": "unauthorized"}, 401

    # Blueprints
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(me_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(templates_bp, url_prefix="/api")
    app.register_blueprint(assets_bp, url_prefix="/api")
    app.register_blueprint(barcodes_bp, url_prefix="/api")
    app.register_blueprint(generate_bp, url_prefix="/api")
    app.register_blueprint(datasets_bp, url_prefix="/api")
    app.register_blueprint(jobs_bp, url_prefix="/api")

    # CLI
    register_cli(app)

    return app
