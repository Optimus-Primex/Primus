"""Tests for the pluggable check-type registry, dispatch, and validation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from primus.services import check_types
from primus.services.check_types import (
    CheckResult,
    CheckType,
    available_types,
    get_check_type,
    register,
)
from primus.services.checker import perform_check
from primus.services.validators import ValidationError, validate_monitor_payload


class EchoCheckType(CheckType):
    """A minimal type that records its type_config and echoes the monitor name."""

    slug = "echo"
    label = "Echo"
    requires_url = True

    def run(self, monitor, *, allow_private=False, user_agent=""):
        return CheckResult(True, None, 1.0, detail={"echo": monitor.name})

    def validate_config(self, config=None, app_config=None):
        cleaned = dict(config or {})
        cleaned.setdefault("greeting", "hi")
        return cleaned


class UrlOptionalCheckType(CheckType):
    slug = "no-url"
    label = "No URL"
    requires_url = False

    def run(self, monitor, *, allow_private=False, user_agent=""):
        return CheckResult(True, None, 2.0)


@pytest.fixture()
def register_temp():
    """Register throwaway check types and remove them afterwards."""

    registered = []

    def _register(check_type):
        register(check_type)
        registered.append(check_type.slug)

    yield _register
    for slug in registered:
        check_types._REGISTRY.pop(slug, None)


def test_http_type_is_registered_by_default():
    http_type = get_check_type("http")
    assert http_type is not None
    assert http_type.slug == "http"
    assert http_type.requires_url is True


def test_type_lookup_is_case_insensitive():
    assert get_check_type("HTTP") is get_check_type("http")


def test_available_types_are_sorted_and_include_http():
    slugs = [check_type.slug for check_type in available_types()]
    assert "http" in slugs
    assert slugs == sorted(slugs)


def test_unknown_type_returns_none():
    assert get_check_type("does-not-exist") is None


def test_perform_check_unknown_type_is_a_failure():
    monitor = SimpleNamespace(type="nope", name="x")
    result = perform_check(monitor, allow_private=True)
    assert not result.success
    assert "Unknown monitor type" in result.error


def test_perform_check_defaults_to_http_without_type():
    monitor = SimpleNamespace(
        name="x", url="http://127.0.0.1:1", method="GET", timeout_seconds=1, expected_status=200
    )
    result = perform_check(monitor, allow_private=True)
    # Falls back to the http type (URL points at a closed port) rather than
    # exploding on the missing ``type`` attribute.
    assert not result.success
    assert result.error


def test_perform_check_dispatches_to_registered_type(register_temp):
    register_temp(EchoCheckType())
    monitor = SimpleNamespace(type="echo", name="dispatcher")
    result = perform_check(monitor, allow_private=True)
    assert result.success
    assert result.detail == {"echo": "dispatcher"}


def test_validate_payload_defaults_to_http(app):
    cleaned = validate_monitor_payload({"name": "x", "url": "https://example.com"}, app.config)
    assert cleaned["type"] == "http"
    assert cleaned["type_config"] == {}


def test_validate_payload_runs_type_config_validation(app, register_temp):
    register_temp(EchoCheckType())
    cleaned = validate_monitor_payload(
        {"name": "x", "url": "https://example.com", "type": "echo"}, app.config
    )
    assert cleaned["type"] == "echo"
    assert cleaned["type_config"] == {"greeting": "hi"}


def test_validate_payload_rejects_unknown_type(app):
    with pytest.raises(ValidationError):
        validate_monitor_payload(
            {"name": "x", "url": "https://example.com", "type": "nope"}, app.config
        )


def test_validate_payload_rejects_non_object_type_config(app):
    with pytest.raises(ValidationError):
        validate_monitor_payload(
            {"name": "x", "url": "https://example.com", "type_config": "nope"}, app.config
        )


def test_validate_payload_url_optional_for_non_url_type(app, register_temp):
    register_temp(UrlOptionalCheckType())
    cleaned = validate_monitor_payload({"name": "x", "type": "no-url"}, app.config)
    assert cleaned["type"] == "no-url"
    assert "url" not in cleaned


def test_api_creates_non_url_monitor(client, api_headers, register_temp):
    register_temp(UrlOptionalCheckType())
    response = client.post(
        "/api/monitors",
        json={"name": "Ping", "type": "no-url", "interval_seconds": 60},
        headers=api_headers,
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["type"] == "no-url"
    assert body["url"] is None
