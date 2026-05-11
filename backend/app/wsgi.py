"""WSGI entrypoint for Gunicorn."""

from app.factory import create_app

app = create_app()
