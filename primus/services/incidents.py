"""Incident state machine.

A monitor moves through:

* ``pending`` -> ``up`` when the first successful check arrives,
* ``up`` -> ``down`` after ``failure_threshold`` consecutive failures (an
  :class:`~primus.models.Incident` is opened),
* ``down`` -> ``up`` when a check succeeds (the open incident is resolved).

Every transition that opens or resolves an incident is reported as an
:class:`IncidentEvent`.  Alerting (a future subsystem) can subscribe to these
events without touching the persistence logic here.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..extensions import db
from ..models import (
    INCIDENT_OPEN,
    INCIDENT_RESOLVED,
    STATUS_DOWN,
    STATUS_UP,
    Check,
    Incident,
    utcnow,
)


@dataclass
class IncidentEvent:
    """A single incident transition produced by :func:`record_check`."""

    kind: str  # "opened" or "resolved"
    incident: Incident


def record_check(monitor, result, failure_threshold: int = 1, now=None):
    """Persist a check result and apply the incident state machine.

    Returns a ``(check, event)`` tuple where ``event`` is ``None`` unless an
    incident was opened or resolved by this check.
    """

    now = now or utcnow()
    check = Check(
        monitor_id=monitor.id,
        success=result.success,
        status_code=result.status_code,
        latency_ms=result.latency_ms,
        error=result.error,
        detail=getattr(result, "detail", None),
        checked_at=now,
    )
    db.session.add(check)

    monitor.last_status = STATUS_UP if result.success else STATUS_DOWN
    monitor.last_status_code = result.status_code
    monitor.last_latency_ms = result.latency_ms
    monitor.last_checked_at = now
    monitor.schedule_next(now)

    event = _apply_incident(monitor, result, failure_threshold, now)
    db.session.commit()
    return check, event


def _apply_incident(monitor, result, failure_threshold, now) -> IncidentEvent | None:
    open_incident = Incident.query.filter_by(monitor_id=monitor.id, status=INCIDENT_OPEN).first()

    if result.success:
        monitor.consecutive_failures = 0
        if open_incident is not None:
            open_incident.status = INCIDENT_RESOLVED
            open_incident.resolved_at = now
            return IncidentEvent("resolved", open_incident)
        return None

    monitor.consecutive_failures = (monitor.consecutive_failures or 0) + 1
    cause = _describe_failure(result)

    if open_incident is not None:
        open_incident.consecutive_failures = monitor.consecutive_failures
        return None

    if monitor.consecutive_failures >= failure_threshold:
        incident = Incident(
            monitor_id=monitor.id,
            status=INCIDENT_OPEN,
            cause=cause,
            consecutive_failures=monitor.consecutive_failures,
            started_at=now,
        )
        db.session.add(incident)
        return IncidentEvent("opened", incident)

    return None


def _describe_failure(result) -> str:
    if result.error:
        return result.error
    if result.status_code is not None:
        return f"HTTP {result.status_code}"
    return "Unreachable"
