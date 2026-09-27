"""HTTP health checker.

The checker never raises for network failures: it always returns a
:class:`CheckResult` describing what happened.  Validation errors are captured
as unsuccessful results with a human-readable ``error`` message.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from .validators import ValidationError, assert_public_host

DEFAULT_USER_AGENT = "Primus-Uptime-Monitor/1.0"
MAX_ERROR_LENGTH = 500


@dataclass
class CheckResult:
    success: bool
    status_code: int | None
    latency_ms: float | None
    error: str | None = None


def _truncate(message: str | None) -> str | None:
    if message is None:
        return None
    return message[:MAX_ERROR_LENGTH]


def perform_check(
    monitor,
    allow_private: bool = False,
    user_agent: str = DEFAULT_USER_AGENT,
) -> CheckResult:
    """Perform a single HTTP request for ``monitor`` and classify the result."""

    parsed = urlparse(monitor.url)
    if parsed.scheme.lower() not in ("http", "https"):
        return CheckResult(False, None, None, _truncate(f"Unsupported scheme: {parsed.scheme!r}"))
    try:
        assert_public_host(parsed.hostname, allow_private)
    except ValidationError as exc:
        return CheckResult(False, None, None, _truncate(str(exc)))

    request = urlrequest.Request(
        monitor.url,
        method=monitor.method,
        headers={"User-Agent": user_agent, "Accept": "*/*"},
    )

    start = time.perf_counter()
    try:
        # Scheme is restricted to http/https above and the host is SSRF-checked.
        with urlrequest.urlopen(  # nosec B310
            request, timeout=monitor.timeout_seconds
        ) as response:
            latency = round((time.perf_counter() - start) * 1000, 2)
            code = response.getcode()
            return _classify(monitor.expected_status, code, latency)
    except HTTPError as exc:  # 4xx/5xx are still valid responses
        latency = round((time.perf_counter() - start) * 1000, 2)
        return _classify(monitor.expected_status, exc.code, latency)
    except (URLError, TimeoutError, OSError) as exc:
        latency = round((time.perf_counter() - start) * 1000, 2)
        return CheckResult(False, None, latency, _truncate(str(exc)))


def _classify(expected: int, code: int | None, latency_ms: float) -> CheckResult:
    if code == expected:
        return CheckResult(True, code, latency_ms)
    return CheckResult(
        False,
        code,
        latency_ms,
        _truncate(f"Expected HTTP {expected}, received {code}"),
    )


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
