"""HTTP(S) check type.

The original (and default) Primus behaviour: send a ``GET``/``HEAD`` request
and compare the response status against ``monitor.expected_status``.
"""

from __future__ import annotations

import time
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from ..validators import ValidationError, assert_public_host
from .base import DEFAULT_USER_AGENT, CheckResult, CheckType, truncate


class HttpCheckType(CheckType):
    slug = "http"
    label = "HTTP(S)"
    description = "Request a URL and assert the response status code."
    requires_url = True

    def run(
        self,
        monitor,
        *,
        allow_private: bool = False,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> CheckResult:
        parsed = urlparse(monitor.url)
        if parsed.scheme.lower() not in ("http", "https"):
            return CheckResult(
                False, None, None, truncate(f"Unsupported scheme: {parsed.scheme!r}")
            )
        try:
            assert_public_host(parsed.hostname, allow_private)
        except ValidationError as exc:
            return CheckResult(False, None, None, truncate(str(exc)))

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
                return _classify(monitor.expected_status, response.getcode(), latency)
        except HTTPError as exc:  # 4xx/5xx are still valid responses
            latency = round((time.perf_counter() - start) * 1000, 2)
            return _classify(monitor.expected_status, exc.code, latency)
        except (URLError, TimeoutError, OSError) as exc:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return CheckResult(False, None, latency, truncate(str(exc)))


def _classify(expected: int, code: int | None, latency_ms: float) -> CheckResult:
    if code == expected:
        return CheckResult(True, code, latency_ms)
    return CheckResult(
        False,
        code,
        latency_ms,
        truncate(f"Expected HTTP {expected}, received {code}"),
    )
