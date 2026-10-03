"""Shared JSON-over-HTTP helper for ecosystem check types.

Stellar Horizon (REST) and Soroban RPC (JSON-RPC) both speak JSON over HTTP,
so the transport and SSRF handling live here instead of being duplicated in
every check type.  Transport failures raise :class:`HttpJsonError`; HTTP error
responses are returned to the caller (they often still carry a useful body).
"""

from __future__ import annotations

import json
import time
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from ..validators import ValidationError, assert_public_host
from .base import DEFAULT_USER_AGENT, truncate


class HttpJsonError(Exception):
    """Raised when a JSON request cannot be completed (DNS, TLS, timeout...)."""


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload=None,
    timeout: int = 10,
    user_agent: str = DEFAULT_USER_AGENT,
    allow_private: bool = False,
    extra_headers: dict | None = None,
) -> tuple[int, object | None, float]:
    """Perform a JSON request and return ``(status_code, data, latency_ms)``.

    ``data`` is the decoded JSON body or ``None`` when the body is empty.
    """

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise HttpJsonError(f"Unsupported scheme: {parsed.scheme!r}")
    try:
        assert_public_host(parsed.hostname, allow_private)
    except ValidationError as exc:
        raise HttpJsonError(truncate(str(exc))) from exc

    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)

    request = urlrequest.Request(url, data=body, method=method, headers=headers)

    start = time.perf_counter()
    try:
        # Scheme is restricted above and the host passed the SSRF check.
        with urlrequest.urlopen(request, timeout=timeout) as response:  # nosec B310
            raw = response.read()
            code = response.getcode()
    except HTTPError as exc:
        raw = exc.read()
        code = exc.code
    except (URLError, TimeoutError, OSError) as exc:
        raise HttpJsonError(truncate(str(exc))) from exc
    latency = round((time.perf_counter() - start) * 1000, 2)

    if not raw:
        return code, None, latency
    try:
        return code, json.loads(raw.decode("utf-8")), latency
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HttpJsonError(f"invalid JSON response: {exc}") from exc


def json_rpc(
    url: str,
    method: str,
    params=None,
    *,
    timeout: int = 10,
    user_agent: str = DEFAULT_USER_AGENT,
    allow_private: bool = False,
) -> tuple[object | None, str | None, float]:
    """Call a JSON-RPC 2.0 method.

    Returns ``(result, error_message, latency_ms)`` where ``error_message`` is
    set for transport failures or a JSON-RPC ``error`` member.
    """

    envelope = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        envelope["params"] = params
    try:
        code, data, latency = request_json(
            url,
            method="POST",
            payload=envelope,
            timeout=timeout,
            user_agent=user_agent,
            allow_private=allow_private,
        )
    except HttpJsonError as exc:
        return None, str(exc), 0.0

    if code >= 500 or not isinstance(data, dict):
        return None, f"RPC returned HTTP {code}", latency
    if data.get("error"):
        error = data["error"]
        message = error.get("message") if isinstance(error, dict) else str(error)
        return None, truncate(f"RPC error: {message}"), latency
    return data.get("result"), None, latency
