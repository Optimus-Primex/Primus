"""Incident state-machine tests."""

from __future__ import annotations

from primus.models import INCIDENT_OPEN, INCIDENT_RESOLVED, Incident
from primus.services.checker import CheckResult
from primus.services.incidents import record_check


def up():
    return CheckResult(True, 200, 12.0)


def down(message="boom"):
    return CheckResult(False, None, None, message)


def test_success_records_check_and_updates_monitor(app, db, sample_monitor):
    check, event = record_check(sample_monitor, up())
    assert event is None
    assert check.success
    assert sample_monitor.last_status == "up"
    assert sample_monitor.last_status_code == 200
    assert sample_monitor.next_check_at is not None


def test_incident_opens_after_threshold(app, db, sample_monitor):
    _, first = record_check(sample_monitor, down(), failure_threshold=2)
    assert first is None
    assert sample_monitor.consecutive_failures == 1

    _, second = record_check(sample_monitor, down("still down"), failure_threshold=2)
    assert second is not None
    assert second.kind == "opened"
    assert second.incident.status == INCIDENT_OPEN
    assert Incident.query.count() == 1


def test_no_incident_before_threshold(app, db, sample_monitor):
    record_check(sample_monitor, down(), failure_threshold=3)
    assert Incident.query.count() == 0
    assert sample_monitor.consecutive_failures == 1


def test_incident_resolves_on_recovery(app, db, sample_monitor):
    record_check(sample_monitor, down(), failure_threshold=1)
    _, event = record_check(sample_monitor, up(), failure_threshold=1)
    assert event is not None
    assert event.kind == "resolved"
    assert event.incident.status == INCIDENT_RESOLVED
    assert sample_monitor.consecutive_failures == 0


def test_open_incident_tracks_failure_count(app, db, sample_monitor):
    record_check(sample_monitor, down(), failure_threshold=1)
    _, event = record_check(sample_monitor, down(), failure_threshold=1)
    assert event is None
    assert Incident.query.one().consecutive_failures == 2
