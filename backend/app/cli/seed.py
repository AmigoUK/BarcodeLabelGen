"""CLI commands for first-run seeding."""

from __future__ import annotations

import os
import secrets

import click
from flask import Flask
from flask.cli import with_appcontext

from app.db.session import get_session
from app.models.user import Role
from app.services.users import EmailAlreadyExistsError, create_user, get_user_by_email


@click.command("seed-admin")
@with_appcontext
def seed_admin() -> None:
    """Create the initial admin user from env vars (idempotent).

    Reads:
        ADMIN_EMAIL    (required)
        ADMIN_PASSWORD (optional — generated if absent and printed once)
    """
    email = os.environ.get("ADMIN_EMAIL")
    if not email:
        raise click.UsageError("ADMIN_EMAIL env var is required")

    session = get_session()
    if get_user_by_email(session, email):
        click.echo(f"Admin user {email} already exists — skipping.")
        return

    password = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(16)
    try:
        create_user(
            session,
            email=email,
            plain_password=password,
            role=Role.ADMIN,
            language="pl",
            must_change_password=True,
        )
    except EmailAlreadyExistsError:
        click.echo(f"Admin user {email} already exists (race) — skipping.")
        return

    click.echo("✅ Initial admin created:")
    click.echo(f"   email:    {email}")
    if "ADMIN_PASSWORD" not in os.environ:
        click.echo(f"   password: {password}    ← write this down, won't be shown again")
        click.echo("   (must change on first login)")


def register_cli(app: Flask) -> None:
    from app.cli.qa import register_qa_cli

    app.cli.add_command(seed_admin)
    register_qa_cli(app)
