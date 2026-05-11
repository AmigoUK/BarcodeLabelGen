"""Flask extension singletons (instantiated once, configured by factory)."""

from __future__ import annotations

from flask_login import LoginManager
from flask_session import Session

login_manager = LoginManager()
session_ext = Session()
