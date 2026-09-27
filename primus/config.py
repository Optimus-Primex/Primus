"""Configuration objects for Primus.

Configuration is environment driven so the same image can run in development,
CI, and production without code changes.  Secrets are never hard-coded: the
``PRIMUS_SECRET_KEY`` and ``PRIMUS_DATABASE_URL`` variables are required in
production (see :func:`validate_production`).
"""

from __future__ import annotations

import os
from datetime import timedelta

from sqlalchemy.pool import StaticPool

TRUE_VALUES = {"1", "true", "yes", "on"}


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class BaseConfig:
    """Settings shared by every environment."""

    # --- Core Flask -----------------------------------------------------
    SECRET_KEY = os.environ.get("PRIMUS_SECRET_KEY", "dev-insecure-change-me")
    PREFERRED_URL_SCHEME = "http"

    # --- Sessions -------------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("PRIMUS_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(days=env_int("PRIMUS_SESSION_DAYS", 14))

    # --- Database -------------------------------------------------------
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Authentication / registration ----------------------------------
    PRIMUS_ALLOW_REGISTRATION = env_bool("PRIMUS_ALLOW_REGISTRATION", True)
    PRIMUS_PASSWORD_MIN_LENGTH = env_int("PRIMUS_PASSWORD_MIN_LENGTH", 8)

    # --- Checker --------------------------------------------------------
    PRIMUS_DEFAULT_TIMEOUT = env_int("PRIMUS_DEFAULT_TIMEOUT", 10)
    PRIMUS_MAX_TIMEOUT = env_int("PRIMUS_MAX_TIMEOUT", 60)
    PRIMUS_MIN_INTERVAL = env_int("PRIMUS_MIN_INTERVAL", 30)
    PRIMUS_MAX_INTERVAL = env_int("PRIMUS_MAX_INTERVAL", 86400)
    PRIMUS_CHECK_RETRIES = env_int("PRIMUS_CHECK_RETRIES", 1)
    PRIMUS_RETRY_DELAY = env_float("PRIMUS_RETRY_DELAY", 2.0)
    PRIMUS_FAILURE_THRESHOLD = env_int("PRIMUS_FAILURE_THRESHOLD", 2)
    PRIMUS_ALLOW_PRIVATE_TARGETS = env_bool("PRIMUS_ALLOW_PRIVATE_TARGETS", False)
    PRIMUS_USER_AGENT = "Primus-Uptime-Monitor/1.0 (+https://github.com/)"

    # --- Scheduler ------------------------------------------------------
    PRIMUS_ENABLE_SCHEDULER = env_bool("PRIMUS_ENABLE_SCHEDULER", False)
    PRIMUS_SCHEDULER_INTERVAL = env_float("PRIMUS_SCHEDULER_INTERVAL", 5.0)
    PRIMUS_WORKER_THREADS = env_int("PRIMUS_WORKER_THREADS", 8)
    PRIMUS_SCHEDULER_BATCH = env_int("PRIMUS_SCHEDULER_BATCH", 50)

    # --- API / pagination ----------------------------------------------
    PRIMUS_HISTORY_LIMIT = env_int("PRIMUS_HISTORY_LIMIT", 100)
    PRIMUS_MAX_PAGE_SIZE = env_int("PRIMUS_MAX_PAGE_SIZE", 200)


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("PRIMUS_DATABASE_URL", "sqlite:///dev.db")


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    # A single shared in-memory connection so the scheduler's worker threads
    # and the request handlers see the same data.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    # Tests exercise the checker against loopback targets, so allow them.
    PRIMUS_ALLOW_PRIVATE_TARGETS = True
    PRIMUS_ENABLE_SCHEDULER = False
    PRIMUS_FAILURE_THRESHOLD = 2


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "PRIMUS_DATABASE_URL", "sqlite:///" + os.path.join("/data", "primus.db")
    )


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def validate_production(app) -> None:
    """Fail fast when a production deployment is misconfigured."""

    if app.config.get("DEBUG"):
        return
    weak_secrets = {None, "", "dev-insecure-change-me"}
    if app.config.get("SECRET_KEY") in weak_secrets:
        raise RuntimeError("PRIMUS_SECRET_KEY must be set to a strong secret in production")
    if "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        # SQLite is acceptable for a single-node deployment but not encrypted;
        # warn the operator rather than crash.
        app.logger.warning(
            "Primus is running on SQLite. Use a server database for multi-process deployments."
        )
