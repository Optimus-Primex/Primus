"""Flask CLI commands (``flask primus ...``)."""

from __future__ import annotations

import time

import click
from flask.cli import with_appcontext


@click.group("primus")
def primus_cli():
    """Primus management commands."""


@primus_cli.command("init-db")
@with_appcontext
def init_db():
    """Create all database tables."""

    from .extensions import db

    db.create_all()
    click.echo("Database tables created.")


@primus_cli.command("create-user")
@click.option("--username", prompt=True)
@click.option("--email", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_user(username, email, password):
    """Create a user account."""

    from .extensions import db
    from .models import User
    from .services.validators import ValidationError, validate_user_credentials

    try:
        validate_user_credentials(username, email, password, _config())
    except ValidationError as exc:
        raise click.ClickException(str(exc)) from exc

    if User.query.filter((User.username == username) | (User.email == email)).first():
        raise click.ClickException("A user with that username or email already exists.")

    user = User(username=username.strip(), email=email.strip().lower())
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Created user {user.username!r}. API token: {user.api_token}")


@primus_cli.command("seed")
@with_appcontext
def seed():
    """Seed a demo user and example monitors (idempotent)."""

    from .extensions import db
    from .models import Monitor, User

    user = User.query.filter_by(username="demo").first()
    if user is None:
        user = User(username="demo", email="demo@example.com")
        user.set_password("demo-password")
        db.session.add(user)
        db.session.flush()

    examples = [
        ("Example", "https://example.com", 300),
        ("HTTPBin status", "https://httpbin.org/status/200", 600),
    ]
    created = 0
    for name, url, interval in examples:
        if not Monitor.query.filter_by(user_id=user.id, url=url).first():
            monitor = Monitor(
                user_id=user.id,
                name=name,
                url=url,
                interval_seconds=interval,
            )
            db.session.add(monitor)
            created += 1
    db.session.commit()
    click.echo(f"Seed complete. Demo login: demo / demo-password. New monitors: {created}")


@primus_cli.command("check-once")
@with_appcontext
def check_once():
    """Run all due checks once, synchronously."""

    from .services.scheduler import Scheduler

    scheduler = Scheduler(_app(), max_workers=1)
    monitor_ids = scheduler.run_once()
    click.echo(f"Checked {len(monitor_ids)} monitor(s).")


@primus_cli.command("worker")
@with_appcontext
def worker():
    """Run the background scheduler in the foreground."""

    from .services.scheduler import Scheduler

    scheduler = Scheduler(_app())
    scheduler.start()
    click.echo("Worker running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:  # pragma: no cover - interactive
        click.echo("Stopping worker...")
    finally:
        scheduler.stop()


def _config():
    from flask import current_app

    return current_app.config


def _app():
    from flask import current_app

    return current_app._get_current_object()


def register_cli(app) -> None:
    app.cli.add_command(primus_cli)
