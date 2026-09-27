"""Dashboard pages and form handling."""

from __future__ import annotations

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    INCIDENT_OPEN,
    STATUS_DOWN,
    STATUS_PENDING,
    STATUS_UP,
    Check,
    Incident,
    Monitor,
)
from ..services.checker import check_with_retries
from ..services.incidents import record_check
from ..services.validators import ValidationError, validate_monitor_payload
from . import bp


@bp.get("/")
@login_required
def index():
    monitors = Monitor.query.filter_by(user_id=current_user.id).order_by(Monitor.name.asc()).all()
    summary = {
        "total": len(monitors),
        "up": sum(1 for m in monitors if m.last_status == STATUS_UP),
        "down": sum(1 for m in monitors if m.last_status == STATUS_DOWN),
        "pending": sum(1 for m in monitors if m.last_status in (None, STATUS_PENDING)),
        "open_incidents": Incident.query.join(Monitor)
        .filter(Monitor.user_id == current_user.id, Incident.status == INCIDENT_OPEN)
        .count(),
    }
    return render_template("dashboard/index.html", monitors=monitors, summary=summary)


@bp.get("/monitors/new")
@login_required
def new_monitor():
    return render_template("dashboard/form.html", monitor=None)


@bp.post("/monitors")
@login_required
def create_monitor():
    try:
        cleaned = validate_monitor_payload(_form_payload(), current_app.config)
    except ValidationError as exc:
        flash(str(exc), "error")
        return render_template("dashboard/form.html", monitor=None, form=request.form), 400

    monitor = Monitor(
        user_id=current_user.id,
        last_status=STATUS_PENDING,
        **cleaned,
    )
    monitor.schedule_next()
    db.session.add(monitor)
    db.session.commit()
    flash(f"Monitor {monitor.name!r} created.", "success")
    return redirect(url_for("dashboard.monitor_detail", monitor_id=monitor.id))


@bp.get("/monitors/<int:monitor_id>")
@login_required
def monitor_detail(monitor_id):
    monitor = _owned_or_404(monitor_id)
    checks = (
        Check.query.filter_by(monitor_id=monitor.id)
        .order_by(Check.checked_at.desc())
        .limit(50)
        .all()
    )
    incidents = (
        Incident.query.filter_by(monitor_id=monitor.id)
        .order_by(Incident.started_at.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "dashboard/detail.html",
        monitor=monitor,
        checks=checks,
        incidents=incidents,
        uptime=monitor.uptime_percentage(),
    )


@bp.get("/monitors/<int:monitor_id>/edit")
@login_required
def edit_monitor(monitor_id):
    monitor = _owned_or_404(monitor_id)
    return render_template("dashboard/form.html", monitor=monitor)


@bp.post("/monitors/<int:monitor_id>")
@login_required
def update_monitor(monitor_id):
    monitor = _owned_or_404(monitor_id)
    try:
        cleaned = validate_monitor_payload(_form_payload(), current_app.config)
    except ValidationError as exc:
        flash(str(exc), "error")
        return (
            render_template("dashboard/form.html", monitor=monitor, form=request.form),
            400,
        )

    for field, value in cleaned.items():
        setattr(monitor, field, value)
    monitor.schedule_next()
    db.session.commit()
    flash("Monitor updated.", "success")
    return redirect(url_for("dashboard.monitor_detail", monitor_id=monitor.id))


@bp.post("/monitors/<int:monitor_id>/toggle")
@login_required
def toggle_monitor(monitor_id):
    monitor = _owned_or_404(monitor_id)
    monitor.enabled = not monitor.enabled
    if monitor.enabled:
        monitor.schedule_next()
    db.session.commit()
    flash("Monitor enabled." if monitor.enabled else "Monitor paused.", "success")
    return redirect(request.referrer or url_for("dashboard.monitor_detail", monitor_id=monitor.id))


@bp.post("/monitors/<int:monitor_id>/delete")
@login_required
def delete_monitor(monitor_id):
    monitor = _owned_or_404(monitor_id)
    name = monitor.name
    db.session.delete(monitor)
    db.session.commit()
    flash(f"Monitor {name!r} deleted.", "success")
    return redirect(url_for("dashboard.index"))


@bp.post("/monitors/<int:monitor_id>/check")
@login_required
def run_check(monitor_id):
    monitor = _owned_or_404(monitor_id)
    config = current_app.config
    result = check_with_retries(
        monitor,
        retries=config["PRIMUS_CHECK_RETRIES"],
        retry_delay=config["PRIMUS_RETRY_DELAY"],
        allow_private=config["PRIMUS_ALLOW_PRIVATE_TARGETS"],
        user_agent=config["PRIMUS_USER_AGENT"],
    )
    _, event = record_check(monitor, result, failure_threshold=config["PRIMUS_FAILURE_THRESHOLD"])
    if event is not None:
        flash(f"Incident {event.kind} for {monitor.name!r}.", "warning")
    elif result.success:
        flash(f"{monitor.name!r} is up.", "success")
    else:
        flash(f"{monitor.name!r} is down: {result.error or 'check failed'}", "error")
    return redirect(url_for("dashboard.monitor_detail", monitor_id=monitor.id))


# -- helpers -------------------------------------------------------------
def _form_payload() -> dict:
    form = request.form
    return {
        "name": form.get("name", ""),
        "url": form.get("url", ""),
        "method": form.get("method", "GET"),
        "expected_status": form.get("expected_status", 200),
        "timeout_seconds": form.get(
            "timeout_seconds", current_app.config["PRIMUS_DEFAULT_TIMEOUT"]
        ),
        "interval_seconds": form.get(
            "interval_seconds", current_app.config["PRIMUS_MIN_INTERVAL"] * 10
        ),
        "enabled": form.get("enabled") == "on",
    }


def _owned_or_404(monitor_id: int) -> Monitor:
    from flask import abort

    monitor = Monitor.query.filter_by(id=monitor_id, user_id=current_user.id).first()
    if monitor is None:
        abort(404)
    return monitor
