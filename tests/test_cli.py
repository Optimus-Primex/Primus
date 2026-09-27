"""CLI command tests (`flask primus ...`)."""

from __future__ import annotations

from primus.models import Check, Monitor, User


def new_runner(app):
    return app.test_cli_runner()


def test_init_db_is_idempotent(app, db):
    result = new_runner(app).invoke(args=["primus", "init-db"])
    assert result.exit_code == 0
    assert "created" in result.output.lower()


def test_create_user_via_cli(app, db):
    result = new_runner(app).invoke(
        args=["primus", "create-user"],
        input="cliuser\ncliuser@example.com\npassword123\npassword123\n",
    )
    assert result.exit_code == 0
    assert User.query.filter_by(username="cliuser").count() == 1


def test_create_user_rejects_duplicate(app, db, user):
    result = new_runner(app).invoke(
        args=["primus", "create-user"],
        input="alice\nnew@example.com\npassword123\npassword123\n",
    )
    assert result.exit_code != 0
    assert User.query.filter_by(email="new@example.com").count() == 0


def test_seed_is_idempotent(app, db):
    runner = new_runner(app)
    assert runner.invoke(args=["primus", "seed"]).exit_code == 0
    assert runner.invoke(args=["primus", "seed"]).exit_code == 0
    assert Monitor.query.count() == 2
    assert User.query.filter_by(username="demo").count() == 1


def test_check_once_runs_due_checks(app, db, user, http_server):
    monitor = Monitor(
        user_id=user.id,
        name="local",
        url=f"{http_server}/ok",
        interval_seconds=60,
        next_check_at=None,
    )
    db.session.add(monitor)
    db.session.commit()

    result = new_runner(app).invoke(args=["primus", "check-once"])
    assert result.exit_code == 0
    assert Check.query.filter_by(monitor_id=monitor.id).count() == 1
