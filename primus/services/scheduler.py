"""Background scheduler.

The scheduler runs inside the web process by default only when
``PRIMUS_ENABLE_SCHEDULER`` is set, but it can also be run as a dedicated
worker (``flask primus worker``) for multi-process deployments.

Design notes
------------
* Due monitors are *claimed* by advancing ``next_check_at`` before the network
  call.  A crashed check therefore does not hot-loop.
* Each check runs in its own application context so failures cannot poison the
  scheduler loop.
* The check function is injectable, which keeps the scheduler unit-testable
  without real network access.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from ..extensions import db
from ..models import Monitor, utcnow
from .checker import check_with_retries
from .incidents import record_check


class Scheduler:
    def __init__(self, app, max_workers=None, poll_interval=None, check_func=None):
        self.app = app
        self.log = app.logger
        self.poll_interval = (
            poll_interval if poll_interval is not None else app.config["PRIMUS_SCHEDULER_INTERVAL"]
        )
        self.max_workers = max_workers or app.config["PRIMUS_WORKER_THREADS"]
        self.check_func = check_func or check_with_retries
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._executor: ThreadPoolExecutor | None = None

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="primus-worker"
        )
        self._thread = threading.Thread(target=self._loop, name="primus-scheduler", daemon=True)
        self._thread.start()
        self.log.info(
            "Scheduler started (workers=%s, poll=%ss)",
            self.max_workers,
            self.poll_interval,
        )

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
        self.log.info("Scheduler stopped")

    # -- loop ------------------------------------------------------------
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.dispatch_due()
            except Exception:  # pragma: no cover - defensive
                self.log.exception("Scheduler tick failed")
            self._stop.wait(self.poll_interval)

    def dispatch_due(self) -> list[int]:
        with self.app.app_context():
            monitor_ids = self.claim_due_monitors()
        executor = self._executor
        if executor is None:
            raise RuntimeError("Scheduler is not running; call start() first")
        for monitor_id in monitor_ids:
            executor.submit(self.run_job, monitor_id)
        return monitor_ids

    def run_once(self) -> list[int]:
        """Synchronously check every currently due monitor.

        Useful for cron-style deployments and deterministic tests.
        """

        with self.app.app_context():
            monitor_ids = self.claim_due_monitors()
        for monitor_id in monitor_ids:
            self.run_job(monitor_id)
        return monitor_ids

    # -- internals -------------------------------------------------------
    def claim_due_monitors(self) -> list[int]:
        """Return ids of due monitors and advance their schedule atomically."""

        now = utcnow()
        due = (
            Monitor.query.filter(
                Monitor.enabled.is_(True),
                db.or_(
                    Monitor.next_check_at.is_(None),
                    Monitor.next_check_at <= now,
                ),
            )
            .order_by(Monitor.next_check_at.is_(None).desc(), Monitor.next_check_at.asc())
            .limit(self.app.config["PRIMUS_SCHEDULER_BATCH"])
            .all()
        )
        monitor_ids = []
        for monitor in due:
            monitor.schedule_next(now)
            monitor_ids.append(monitor.id)
        db.session.commit()
        return monitor_ids

    def run_job(self, monitor_id: int):
        """Fetch a monitor and execute a single check with retries."""

        with self.app.app_context():
            monitor = db.session.get(Monitor, monitor_id)
            if monitor is None or not monitor.enabled:
                return None
            result = self.check_func(
                monitor,
                retries=self.app.config["PRIMUS_CHECK_RETRIES"],
                retry_delay=self.app.config["PRIMUS_RETRY_DELAY"],
                allow_private=self.app.config["PRIMUS_ALLOW_PRIVATE_TARGETS"],
                user_agent=self.app.config["PRIMUS_USER_AGENT"],
            )
            _, event = record_check(
                monitor,
                result,
                failure_threshold=self.app.config["PRIMUS_FAILURE_THRESHOLD"],
            )
            if event is not None:
                self.log.info(
                    "Incident %s for monitor %s (%s)",
                    event.kind,
                    monitor.id,
                    monitor.name,
                )
            return event


def start_scheduler_from_config(app):
    """Start the in-process scheduler if enabled; otherwise return ``None``."""

    if not app.config.get("PRIMUS_ENABLE_SCHEDULER"):
        return None
    scheduler = Scheduler(app)
    scheduler.start()
    return scheduler
