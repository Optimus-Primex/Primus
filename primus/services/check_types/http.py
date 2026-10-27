"""HTTP(S) check type.

The original (and default) Primus behaviour: send a ``GET``/``HEAD`` request
and compare the response status against ``monitor.expected_status``.
"""

from __future__ import annotations

import time
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse

from ..validators import (
    MAX_REDIRECTS,
    ValidationError,
    assert_public_host,
    build_safe_opener_with_handler,
)
from .base import DEFAULT_USER_AGENT, CheckResult, CheckType, truncate

REDIRECT_POLICIES = {"follow", "no-follow"}
MAX_REDIRECTS_LIMIT = 20


class HttpCheckType(CheckType):
    slug = "http"
    label = "HTTP(S)"
    description = "Request a URL and assert the response status code."
    requires_url = True

    def validate_config(self, config: dict | None = None, app_config=None) -> dict:
        cleaned = dict(config or {})
        if "redirect_policy" in cleaned:
            policy = str(cleaned["redirect_policy"]).strip().lower()
            if policy not in REDIRECT_POLICIES:
                raise ValidationError("redirect_policy must be 'follow' or 'no-follow'")
            cleaned["redirect_policy"] = policy
        if "max_redirects" in cleaned:
            try:
                max_redirects = int(cleaned["max_redirects"])
            except (TypeError, ValueError):
                raise ValidationError("max_redirects must be an integer") from None
            if not 0 <= max_redirects <= MAX_REDIRECTS_LIMIT:
                raise ValidationError(f"max_redirects must be between 0 and {MAX_REDIRECTS_LIMIT}")
            cleaned["max_redirects"] = max_redirects
        return cleaned

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

        config = getattr(monitor, "type_config", None) or {}
        follow_redirects, max_redirects = _redirect_settings(config)
        policy = "follow" if follow_redirects else "no-follow"

        opener, handler = build_safe_opener_with_handler(
            allow_private,
            follow_redirects=follow_redirects,
            max_redirects=max_redirects,
            initial_url=monitor.url,
        )
        start = time.perf_counter()
        try:
            # Scheme is restricted to http/https above; the opener re-checks
            # every redirect target before following it.
            with opener.open(  # nosec B310
                request, timeout=monitor.timeout_seconds
            ) as response:
                latency = round((time.perf_counter() - start) * 1000, 2)
                detail = _redirect_detail(
                    policy=policy,
                    chain=handler.redirect_chain,
                    final_url=response.geturl(),
                    location=handler.blocked_location,
                )
                return _classify(
                    monitor.expected_status, response.getcode(), latency, detail=detail
                )
        except HTTPError as exc:  # 3xx/4xx/5xx are still valid responses
            latency = round((time.perf_counter() - start) * 1000, 2)
            location = exc.headers.get("Location") if exc.headers else None
            if location:
                location = urljoin(monitor.url, location)
            detail = _redirect_detail(
                policy=policy,
                chain=handler.redirect_chain,
                # With no-follow the 3xx came from the original URL; exc.url is
                # the redirect target that was deliberately not fetched.
                final_url=monitor.url
                if handler.blocked_location
                else (getattr(exc, "url", None) or monitor.url),
                location=location,
            )
            return _classify(monitor.expected_status, exc.code, latency, detail=detail)
        except (URLError, TimeoutError, OSError) as exc:
            latency = round((time.perf_counter() - start) * 1000, 2)
            detail = _redirect_detail(
                policy=policy,
                chain=handler.redirect_chain,
                final_url=handler.redirect_chain[-1] if handler.redirect_chain else monitor.url,
            )
            return CheckResult(False, None, latency, truncate(str(exc)), detail=detail)


def _redirect_settings(config: dict) -> tuple[bool, int]:
    policy = str(config.get("redirect_policy") or "follow").strip().lower()
    follow = policy != "no-follow"
    try:
        max_redirects = int(config.get("max_redirects", MAX_REDIRECTS))
    except (TypeError, ValueError):
        max_redirects = MAX_REDIRECTS
    return follow, max(0, min(max_redirects, MAX_REDIRECTS_LIMIT))


def _redirect_detail(
    *,
    policy: str,
    chain: list[str],
    final_url: str | None,
    location: str | None = None,
) -> dict:
    detail = {
        "redirect_policy": policy,
        "final_url": final_url,
        "redirect_chain": list(chain),
        "redirect_count": len(chain),
    }
    if location:
        detail["redirect_location"] = location
    return detail


def _classify(
    expected: int,
    code: int | None,
    latency_ms: float,
    *,
    detail: dict | None = None,
) -> CheckResult:
    if code == expected:
        return CheckResult(True, code, latency_ms, detail=detail)
    return CheckResult(
        False,
        code,
        latency_ms,
        truncate(f"Expected HTTP {expected}, received {code}"),
        detail=detail,
    )
