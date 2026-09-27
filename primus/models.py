"""SQLAlchemy models for Primus.

Data model overview::

    User 1---* Monitor 1---* Check
                     \\---* Incident

All timestamps are stored as *naive UTC* so that SQLite and server databases
behave consistently.  Use :func:`utcnow` everywhere.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

STATUS_UP = "up"
STATUS_DOWN = "down"
STATUS_PENDING = "pending"

INCIDENT_OPEN = "open"
INCIDENT_RESOLVED = "resolved"


def utcnow() -> datetime:
    """Return the current time as a naive UTC datetime."""

    return datetime.now(UTC).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    api_token = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: secrets.token_urlsafe(32),
    )
    is_enabled = db.Column("is_active", db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    monitors = db.relationship(
        "Monitor",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_active(self) -> bool:  # consumed by Flask-Login
        return bool(self.is_enabled)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def rotate_api_token(self) -> str:
        self.api_token = secrets.token_urlsafe(32)
        return self.api_token

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.username!r}>"


class Monitor(db.Model):
    __tablename__ = "monitors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(120), nullable=False)
    url = db.Column(db.String(2048), nullable=False)
    method = db.Column(db.String(8), nullable=False, default="GET")
    expected_status = db.Column(db.Integer, nullable=False, default=200)
    timeout_seconds = db.Column(db.Integer, nullable=False, default=10)
    interval_seconds = db.Column(db.Integer, nullable=False, default=300)
    enabled = db.Column(db.Boolean, nullable=False, default=True)

    # Denormalised "latest check" fields keep the dashboard query cheap.
    last_status = db.Column(db.String(16), nullable=True, default=STATUS_PENDING)
    last_status_code = db.Column(db.Integer, nullable=True)
    last_latency_ms = db.Column(db.Float, nullable=True)
    last_checked_at = db.Column(db.DateTime, nullable=True)
    next_check_at = db.Column(db.DateTime, nullable=True, index=True)
    consecutive_failures = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    owner = db.relationship("User", back_populates="monitors")
    checks = db.relationship(
        "Check",
        back_populates="monitor",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="Check.checked_at.desc()",
    )
    incidents = db.relationship(
        "Incident",
        back_populates="monitor",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="Incident.started_at.desc()",
    )

    __table_args__ = (db.Index("ix_monitors_due", "enabled", "next_check_at"),)

    # -- computed helpers ------------------------------------------------
    @property
    def is_up(self) -> bool:
        return self.last_status == STATUS_UP

    def schedule_next(self, reference: datetime | None = None) -> datetime:
        reference = reference or utcnow()
        self.next_check_at = reference + timedelta(seconds=self.interval_seconds)
        return self.next_check_at

    def uptime_percentage(self, limit: int = 100) -> float | None:
        """Uptime over the most recent ``limit`` checks (``None`` if no data)."""

        recent = self.checks.limit(limit).all()
        if not recent:
            return None
        successes = sum(1 for check in recent if check.success)
        return round(successes / len(recent) * 100, 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "method": self.method,
            "expected_status": self.expected_status,
            "timeout_seconds": self.timeout_seconds,
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "status": self.last_status,
            "last_status_code": self.last_status_code,
            "last_latency_ms": self.last_latency_ms,
            "last_checked_at": _iso(self.last_checked_at),
            "next_check_at": _iso(self.next_check_at),
            "consecutive_failures": self.consecutive_failures,
            "uptime_percentage": self.uptime_percentage(),
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Monitor {self.name!r} {self.url!r}>"


class Check(db.Model):
    __tablename__ = "checks"

    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)
    monitor_id = db.Column(
        db.Integer,
        db.ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    success = db.Column(db.Boolean, nullable=False)
    status_code = db.Column(db.Integer, nullable=True)
    latency_ms = db.Column(db.Float, nullable=True)
    error = db.Column(db.String(512), nullable=True)
    checked_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    monitor = db.relationship("Monitor", back_populates="checks")

    __table_args__ = (db.Index("ix_checks_monitor_checked", "monitor_id", "checked_at"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "monitor_id": self.monitor_id,
            "success": self.success,
            "status_code": self.status_code,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "checked_at": _iso(self.checked_at),
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Check monitor={self.monitor_id} success={self.success}>"


class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    monitor_id = db.Column(
        db.Integer,
        db.ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(db.String(16), nullable=False, default=INCIDENT_OPEN)
    cause = db.Column(db.String(512), nullable=True)
    consecutive_failures = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    monitor = db.relationship("Monitor", back_populates="incidents")

    __table_args__ = (db.Index("ix_incidents_monitor_status", "monitor_id", "status"),)

    @property
    def is_open(self) -> bool:
        return self.status == INCIDENT_OPEN

    @property
    def duration_seconds(self) -> int:
        end = self.resolved_at or utcnow()
        return max(0, int((end - self.started_at).total_seconds()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "monitor_id": self.monitor_id,
            "status": self.status,
            "cause": self.cause,
            "consecutive_failures": self.consecutive_failures,
            "started_at": _iso(self.started_at),
            "resolved_at": _iso(self.resolved_at),
            "duration_seconds": self.duration_seconds,
        }

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Incident monitor={self.monitor_id} {self.status}>"


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
