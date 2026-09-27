"""Scheduler tests using an injected check function (no real network)."""

from __future__ import annotations

from primus.models import Check, Monitor
from primus.services.checker import CheckResult
from primus.services.scheduler import Scheduler


def success(monitor, **_kwargs):
    return CheckResult(True, 200, 5.0)


def failure(monitor, **_kwargs):
    return CheckResult(False, None, None, "boom")


def reload(db, monitor):
    db.session.expire_all()
    return db.session.get(Monitor, monitor.id)


def make_due(db, monitor):
    """A freshly created monitor is scheduled in the future; force it due."""

    monitor.next_check_at = None
    db.session.commit()


def test_run_once_checks_due_monitors(app, db, sample_monitor):
    make_due(db, sample_monitor)
    scheduler = Scheduler(app, check_func=success)
    checked = scheduler.run_once()
    assert checked == [sample_monitor.id]
    assert Check.query.filter_by(monitor_id=sample_monitor.id).count() == 1
    refreshed = reload(db, sample_monitor)
    assert refreshed.last_status == "up"


def test_run_once_skips_disabled_monitors(app, db, sample_monitor):
    sample_monitor.enabled = False
    db.session.commit()
    scheduler = Scheduler(app, check_func=success)
    assert scheduler.run_once() == []
    assert Check.query.count() == 0


def test_claiming_advances_next_check_time(app, db, sample_monitor):
    sample_monitor.next_check_at = None
    db.session.commit()

    scheduler = Scheduler(app, check_func=success)
    assert scheduler.run_once() == [sample_monitor.id]
    # The monitor is scheduled in the future, so a second pass finds nothing.
    assert scheduler.run_once() == []


def test_scheduler_opens_incident_on_failure(app, db, sample_monitor):
    app.config["PRIMUS_FAILURE_THRESHOLD"] = 1
    make_due(db, sample_monitor)
    scheduler = Scheduler(app, check_func=failure)
    scheduler.run_once()
    from primus.models import Incident

    assert Incident.query.filter_by(monitor_id=sample_monitor.id).count() == 1
