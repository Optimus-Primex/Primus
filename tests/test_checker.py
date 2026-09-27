"""HTTP checker tests (including a real loopback server)."""

from __future__ import annotations

from types import SimpleNamespace

from primus.services.checker import CheckResult, check_with_retries, perform_check


def make_monitor(url, method="GET", timeout=5, expected=200):
    return SimpleNamespace(
        url=url, method=method, timeout_seconds=timeout, expected_status=expected
    )


def test_perform_check_success(http_server):
    result = perform_check(make_monitor(f"{http_server}/ok"), allow_private=True)
    assert result.success
    assert result.status_code == 200
    assert result.latency_ms is not None


def test_perform_check_detects_unexpected_status(http_server):
    result = perform_check(make_monitor(f"{http_server}/bad"), allow_private=True)
    assert not result.success
    assert result.status_code == 500
    assert "Expected HTTP 200" in result.error


def test_perform_check_honours_expected_status(http_server):
    result = perform_check(make_monitor(f"{http_server}/missing", expected=404), allow_private=True)
    assert result.success
    assert result.status_code == 404


def test_perform_check_supports_head(http_server):
    result = perform_check(make_monitor(f"{http_server}/ok", method="HEAD"), allow_private=True)
    assert result.success


def test_perform_check_reports_connection_errors():
    result = perform_check(make_monitor("http://127.0.0.1:1"), allow_private=True)
    assert not result.success
    assert result.error


def test_perform_check_blocks_private_hosts_by_default():
    result = perform_check(make_monitor("http://127.0.0.1:1"), allow_private=False)
    assert not result.success
    assert "non-public" in result.error


def test_check_with_retries_stops_after_success(monkeypatch):
    calls = []

    def fake(monitor, allow_private=False, user_agent=""):
        calls.append(monitor.url)
        return CheckResult(True, 200, 1.0)

    monkeypatch.setattr("primus.services.checker.perform_check", fake)
    result = check_with_retries(
        make_monitor("https://example.com"), retries=3, sleep=lambda _: None
    )
    assert result.success
    assert len(calls) == 1


def test_check_with_retries_exhausts_attempts(monkeypatch):
    calls = []

    def fake(monitor, allow_private=False, user_agent=""):
        calls.append(monitor.url)
        return CheckResult(False, None, 1.0, "boom")

    monkeypatch.setattr("primus.services.checker.perform_check", fake)
    result = check_with_retries(
        make_monitor("https://example.com"), retries=2, sleep=lambda _: None
    )
    assert not result.success
    assert len(calls) == 3
