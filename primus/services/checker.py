"""Check dispatcher.

The dispatcher resolves the check type registered for ``monitor.type`` and
delegates the work to it.  It never raises for network/validation failures: it
always returns a :class:`CheckResult` describing what happened.  Validation
errors are captured as unsuccessful results with a human-readable ``error``.
"""

from __future__ import annotations

import time

from .check_types import (
    DEFAULT_TYPE,
    DEFAULT_USER_AGENT,
    CheckResult,
    get_check_type,
    truncate,
)

__all__ = ["CheckResult", "DEFAULT_USER_AGENT", "check_with_retries", "perform_check"]


def perform_check(
    monitor,
    allow_private: bool = False,
    user_agent: str = DEFAULT_USER_AGENT,
) -> CheckResult:
    """Run a single check for ``monitor`` using its registered check type."""

    slug = getattr(monitor, "type", None) or DEFAULT_TYPE
    check_type = get_check_type(slug)
    if check_type is None:
        return CheckResult(False, None, None, truncate(f"Unknown monitor type: {slug!r}"))
    return check_type.run(monitor, allow_private=allow_private, user_agent=user_agent)


def check_with_retries(
    monitor,
    retries: int = 0,
    retry_delay: float = 0.0,
    allow_private: bool = False,
    user_agent: str = DEFAULT_USER_AGENT,
    sleep=time.sleep,
) -> CheckResult:
    """Run :func:`perform_check`, retrying transient failures.

    A retry only happens while previous attempts failed.  The final attempt's
    result is always returned.
    """

    attempts = max(1, retries + 1)
    result = CheckResult(False, None, None, "no attempt performed")
    for attempt in range(attempts):
        result = perform_check(monitor, allow_private=allow_private, user_agent=user_agent)
        if result.success:
            return result
        if attempt < attempts - 1 and retry_delay:
            sleep(retry_delay)
    return result
