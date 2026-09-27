"""Input validation and SSRF protection helpers.

Because Primus makes outbound HTTP requests to user supplied URLs, URL
validation is a security boundary.  We always validate the *shape* of a URL and
-- at request time -- verify that the host resolves only to public addresses
unless ``PRIMUS_ALLOW_PRIVATE_TARGETS`` is enabled.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

ALLOWED_METHODS = {"GET", "HEAD"}
ALLOWED_SCHEMES = {"http", "https"}

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(ValueError):
    """Raised when untrusted input fails validation."""


def assert_public_host(hostname: str, allow_private: bool = False) -> None:
    """Ensure ``hostname`` never resolves to a private/internal address.

    Disabled entirely when ``allow_private`` is true (self-hosted users often
    monitor internal services).
    """

    if allow_private:
        return
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValidationError(f"Could not resolve host: {hostname}") from exc
    for info in infos:
        address = info[4][0]
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValidationError(
                "Target host resolves to a non-public address; "
                "set PRIMUS_ALLOW_PRIVATE_TARGETS=1 to monitor internal services"
            )


def validate_url(url: str, allow_private: bool = False, resolve: bool = False) -> str:
    if not isinstance(url, str) or not url.strip():
        raise ValidationError("url is required")
    url = url.strip()
    if len(url) > 2048:
        raise ValidationError("url must be at most 2048 characters")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValidationError("url scheme must be http or https")
    if not parsed.hostname:
        raise ValidationError("url must include a hostname")
    if parsed.username or parsed.password:
        raise ValidationError("credentials embedded in the url are not allowed")
    # Reject control characters and raw whitespace that could be used for
    # header injection or ambiguous parsing.
    if any(ord(char) < 32 for char in url):
        raise ValidationError("url contains invalid control characters")
    if any(char.isspace() for char in url):
        raise ValidationError("url must not contain whitespace (use %20)")
    if resolve:
        assert_public_host(parsed.hostname, allow_private)
    return url


def _clean_int(value, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field} must be an integer") from None


def validate_monitor_payload(data: dict, config, partial: bool = False) -> dict:
    """Validate and normalise a monitor create/update payload.

    Returns a dict containing only the fields that were supplied.  Raises
    :class:`ValidationError` on the first problem (the API surfaces the message).
    """

    if not isinstance(data, dict):
        raise ValidationError("payload must be a JSON object")

    cleaned: dict = {}
    allow_private = config["PRIMUS_ALLOW_PRIVATE_TARGETS"]
    defaults = {
        "method": "GET",
        "expected_status": 200,
        "timeout_seconds": config["PRIMUS_DEFAULT_TIMEOUT"],
        "interval_seconds": config["PRIMUS_MIN_INTERVAL"] * 10,
        "enabled": True,
    }

    if not partial:
        for field in ("name", "url"):
            if not data.get(field):
                raise ValidationError(f"{field} is required")

    if "name" in data:
        name = str(data["name"]).strip()
        if not name:
            raise ValidationError("name must not be empty")
        if len(name) > 120:
            raise ValidationError("name must be at most 120 characters")
        cleaned["name"] = name

    if "url" in data:
        cleaned["url"] = validate_url(data["url"], allow_private=allow_private, resolve=False)

    if "method" in data:
        method = str(data["method"]).strip().upper()
        if method not in ALLOWED_METHODS:
            raise ValidationError("method must be GET or HEAD")
        cleaned["method"] = method

    if "expected_status" in data:
        status = _clean_int(data["expected_status"], "expected_status")
        if not 100 <= status <= 599:
            raise ValidationError("expected_status must be between 100 and 599")
        cleaned["expected_status"] = status

    if "timeout_seconds" in data:
        timeout = _clean_int(data["timeout_seconds"], "timeout_seconds")
        if not 1 <= timeout <= config["PRIMUS_MAX_TIMEOUT"]:
            raise ValidationError(
                f"timeout_seconds must be between 1 and {config['PRIMUS_MAX_TIMEOUT']}"
            )
        cleaned["timeout_seconds"] = timeout

    if "interval_seconds" in data:
        interval = _clean_int(data["interval_seconds"], "interval_seconds")
        if not config["PRIMUS_MIN_INTERVAL"] <= interval <= config["PRIMUS_MAX_INTERVAL"]:
            raise ValidationError(
                "interval_seconds must be between "
                f"{config['PRIMUS_MIN_INTERVAL']} and {config['PRIMUS_MAX_INTERVAL']}"
            )
        cleaned["interval_seconds"] = interval

    if "enabled" in data:
        cleaned["enabled"] = bool(data["enabled"])

    if not partial:
        for field, value in defaults.items():
            cleaned.setdefault(field, value)

    return cleaned


def validate_user_credentials(username, email, password, config) -> dict:
    """Validate registration/CLI credentials, returning normalised values."""

    if not isinstance(username, str) or not USERNAME_RE.match(username.strip()):
        raise ValidationError(
            "username must be 3-64 characters using letters, digits, '.', '_' or '-'"
        )
    if not isinstance(email, str) or len(email) > 255 or not EMAIL_RE.match(email.strip()):
        raise ValidationError("a valid email address is required")
    min_length = config.get("PRIMUS_PASSWORD_MIN_LENGTH", 8)
    if not isinstance(password, str) or len(password) < min_length:
        raise ValidationError(f"password must be at least {min_length} characters")
    return {
        "username": username.strip(),
        "email": email.strip().lower(),
        "password": password,
    }
