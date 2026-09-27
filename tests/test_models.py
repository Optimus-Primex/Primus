"""Model behaviour tests."""

from __future__ import annotations

from datetime import timedelta

from primus.models import Check, Incident, utcnow


def test_password_is_hashed(app, user):
    assert user.password_hash != "password123"
    assert user.check_password("password123")
    assert not user.check_password("wrong")


def test_api_token_can_be_rotated(app, user):
    original = user.api_token
    rotated = user.rotate_api_token()
    assert rotated != original
    assert user.api_token == rotated


def test_schedule_next_is_in_the_future(app, sample_monitor):
    scheduled = sample_monitor.schedule_next()
    assert scheduled > utcnow()


def test_uptime_percentage(app, db, sample_monitor):
    assert sample_monitor.uptime_percentage() is None
    now = utcnow()
    for success in (True, True, False, True):
        db.session.add(Check(monitor_id=sample_monitor.id, success=success, checked_at=now))
    db.session.commit()
    assert sample_monitor.uptime_percentage() == 75.0


def test_monitor_to_dict_contains_expected_keys(sample_monitor):
    data = sample_monitor.to_dict()
    for key in ("id", "name", "url", "status", "uptime_percentage", "interval_seconds"):
        assert key in data


def test_incident_duration_and_serialisation(app, db, sample_monitor):
    started = utcnow() - timedelta(seconds=90)
    incident = Incident(monitor_id=sample_monitor.id, started_at=started, resolved_at=utcnow())
    db.session.add(incident)
    db.session.commit()
    assert incident.duration_seconds >= 89
    assert incident.to_dict()["status"] == "open"
