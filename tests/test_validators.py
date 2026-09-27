"""Tests for the validation and SSRF-protection helpers."""

from __future__ import annotations

import pytest

from primus.services.validators import (
    ValidationError,
    assert_public_host,
    validate_monitor_payload,
    validate_url,
    validate_user_credentials,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://example.com/path?query=1",
        "https://sub.example.com:8443/health",
    ],
)
def test_validate_url_accepts_http_and_https(url):
    assert validate_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "ftp://example.com",
        "javascript:alert(1)",
        "https://user:pass@example.com",
        "https://",
        "https://exa mple.com",
    ],
)
def test_validate_url_rejects_bad_input(url):
    with pytest.raises(ValidationError):
        validate_url(url)


def test_validate_url_rejects_control_characters():
    with pytest.raises(ValidationError):
        validate_url("https://example.com/\r\nHost: evil")


def test_public_host_guard_blocks_loopback():
    with pytest.raises(ValidationError):
        assert_public_host("127.0.0.1")


def test_public_host_guard_can_be_disabled():
    assert_public_host("127.0.0.1", allow_private=True)


def test_validate_monitor_payload_applies_defaults(app):
    cleaned = validate_monitor_payload(
        {"name": "My site", "url": "https://example.com"}, app.config
    )
    assert cleaned["name"] == "My site"
    assert cleaned["method"] == "GET"
    assert cleaned["expected_status"] == 200
    assert cleaned["enabled"] is True
    assert cleaned["interval_seconds"] > 0


def test_validate_monitor_payload_requires_fields(app):
    with pytest.raises(ValidationError):
        validate_monitor_payload({"name": "no url"}, app.config)


def test_validate_monitor_payload_rejects_bad_interval(app):
    too_small = app.config["PRIMUS_MIN_INTERVAL"] - 1
    with pytest.raises(ValidationError):
        validate_monitor_payload(
            {"name": "x", "url": "https://example.com", "interval_seconds": too_small},
            app.config,
        )


def test_validate_monitor_payload_rejects_bad_method(app):
    with pytest.raises(ValidationError):
        validate_monitor_payload(
            {"name": "x", "url": "https://example.com", "method": "POST"}, app.config
        )


def test_validate_user_credentials_normalises_email(app):
    cleaned = validate_user_credentials("Alice_1", "Alice@Example.COM", "supersecret", app.config)
    assert cleaned["email"] == "alice@example.com"
    assert cleaned["username"] == "Alice_1"


@pytest.mark.parametrize(
    "username,email,password",
    [
        ("ab", "a@b.com", "supersecret"),
        ("okname", "not-an-email", "supersecret"),
        ("okname", "a@b.com", "short"),
    ],
)
def test_validate_user_credentials_rejects_bad_input(app, username, email, password):
    with pytest.raises(ValidationError):
        validate_user_credentials(username, email, password, app.config)
