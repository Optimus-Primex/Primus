"""REST endpoints for monitors, checks, incidents, and health."""

from __future__ import annotations

from flask import current_app, g, jsonify, request
from sqlalchemy import text

from ..extensions import db
from ..models import STATUS_PENDING, Check, Incident, Monitor
from ..services.checker import check_with_retries
from ..services.incidents import record_check
from ..services.validators import ValidationError, validate_monitor_payload
from . import bp
from .auth import api_auth_required


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _page_limit() -> int:
    default = current_app.config["PRIMUS_HISTORY_LIMIT"]
    raw = request.args.get("limit", default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, current_app.config["PRIMUS_MAX_PAGE_SIZE"]))


def _owned_monitor(monitor_id: int) -> Monitor | None:
    return Monitor.query.filter_by(id=monitor_id, user_id=g.api_user.id).first()


@bp.get("/health")
def health():
    """Liveness/readiness probe (unauthenticated)."""

    database_ok = True
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - defensive
        database_ok = False
    payload = {"status": "ok" if database_ok else "degraded", "database": database_ok}
    return jsonify(payload), (200 if database_ok else 503)


@bp.get("/monitors")
@api_auth_required
def list_monitors():
    monitors = Monitor.query.filter_by(user_id=g.api_user.id).order_by(Monitor.id.asc()).all()
    uptimes = Monitor.uptime_map(monitors)
    return jsonify(
        {"monitors": [monitor.to_dict(uptime=uptimes.get(monitor.id)) for monitor in monitors]}
    )


@bp.post("/monitors")
@api_auth_required
def create_monitor():
    data = request.get_json(silent=True)
    if data is None:
        return _error("request body must be valid JSON", 400)
    try:
        cleaned = validate_monitor_payload(data, current_app.config, partial=False)
    except ValidationError as exc:
        return _error(str(exc), 422)

    monitor = Monitor(user_id=g.api_user.id, last_status=STATUS_PENDING, **cleaned)
    monitor.schedule_next()
    db.session.add(monitor)
    db.session.commit()
    return jsonify(monitor.to_dict()), 201


@bp.get("/monitors/<int:monitor_id>")
@api_auth_required
def get_monitor(monitor_id):
    monitor = _owned_monitor(monitor_id)
    if monitor is None:
        return _error("monitor not found", 404)
    return jsonify(monitor.to_dict())


@bp.patch("/monitors/<int:monitor_id>")
@api_auth_required
def update_monitor(monitor_id):
    monitor = _owned_monitor(monitor_id)
    if monitor is None:
        return _error("monitor not found", 404)
    data = request.get_json(silent=True)
    if data is None:
        return _error("request body must be valid JSON", 400)
    try:
        cleaned = validate_monitor_payload(data, current_app.config, partial=True)
    except ValidationError as exc:
        return _error(str(exc), 422)

    for field, value in cleaned.items():
        setattr(monitor, field, value)
    if "interval_seconds" in cleaned:
        monitor.schedule_next()
    db.session.commit()
    return jsonify(monitor.to_dict())


@bp.delete("/monitors/<int:monitor_id>")
@api_auth_required
def delete_monitor(monitor_id):
    monitor = _owned_monitor(monitor_id)
    if monitor is None:
        return _error("monitor not found", 404)
    db.session.delete(monitor)
    db.session.commit()
    return "", 204


@bp.post("/monitors/<int:monitor_id>/check")
@api_auth_required
def run_check(monitor_id):
    monitor = _owned_monitor(monitor_id)
    if monitor is None:
        return _error("monitor not found", 404)

    config = current_app.config
    result = check_with_retries(
        monitor,
        retries=config["PRIMUS_CHECK_RETRIES"],
        retry_delay=config["PRIMUS_RETRY_DELAY"],
        allow_private=config["PRIMUS_ALLOW_PRIVATE_TARGETS"],
        user_agent=config["PRIMUS_USER_AGENT"],
    )
    check, event = record_check(
        monitor, result, failure_threshold=config["PRIMUS_FAILURE_THRESHOLD"]
    )
    payload = {"check": check.to_dict(), "monitor": monitor.to_dict()}
    if event is not None:
        payload["event"] = event.kind
        payload["incident"] = event.incident.to_dict()
    return jsonify(payload), 201


@bp.get("/monitors/<int:monitor_id>/checks")
@api_auth_required
def list_checks(monitor_id):
    monitor = _owned_monitor(monitor_id)
    if monitor is None:
        return _error("monitor not found", 404)
    checks = (
        Check.query.filter_by(monitor_id=monitor.id)
        .order_by(Check.checked_at.desc())
        .limit(_page_limit())
        .all()
    )
    return jsonify({"checks": [check.to_dict() for check in checks]})


@bp.get("/monitors/<int:monitor_id>/incidents")
@api_auth_required
def list_monitor_incidents(monitor_id):
    monitor = _owned_monitor(monitor_id)
    if monitor is None:
        return _error("monitor not found", 404)
    incidents = (
        Incident.query.filter_by(monitor_id=monitor.id)
        .order_by(Incident.started_at.desc())
        .limit(_page_limit())
        .all()
    )
    return jsonify({"incidents": [incident.to_dict() for incident in incidents]})


@bp.get("/incidents")
@api_auth_required
def list_incidents():
    status = request.args.get("status")
    query = Incident.query.join(Monitor).filter(Monitor.user_id == g.api_user.id)
    if status in {"open", "resolved"}:
        query = query.filter(Incident.status == status)
    incidents = query.order_by(Incident.started_at.desc()).limit(_page_limit()).all()
    return jsonify({"incidents": [incident.to_dict() for incident in incidents]})
