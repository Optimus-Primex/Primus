"""REST API tests."""

from __future__ import annotations

from primus.services.checker import CheckResult
from primus.services.incidents import record_check


def test_health_is_public(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": True}


def test_monitors_require_authentication(client):
    assert client.get("/api/monitors").status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get("/api/monitors", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_list_monitors_is_empty_initially(client, api_headers):
    response = client.get("/api/monitors", headers=api_headers)
    assert response.status_code == 200
    assert response.get_json()["monitors"] == []


def test_create_and_fetch_monitor(client, api_headers, http_server):
    response = client.post(
        "/api/monitors",
        json={"name": "Site", "url": f"{http_server}/ok", "interval_seconds": 60},
        headers=api_headers,
    )
    assert response.status_code == 201
    monitor = response.get_json()
    assert monitor["name"] == "Site"
    assert monitor["status"] == "pending"

    fetched = client.get(f"/api/monitors/{monitor['id']}", headers=api_headers)
    assert fetched.status_code == 200
    assert fetched.get_json()["id"] == monitor["id"]


def test_create_monitor_validation_error(client, api_headers):
    response = client.post(
        "/api/monitors",
        json={"name": "x", "url": "ftp://example.com"},
        headers=api_headers,
    )
    assert response.status_code == 422


def test_create_monitor_requires_json(client, api_headers):
    response = client.post(
        "/api/monitors",
        data="not json",
        headers=api_headers,
        content_type="text/plain",
    )
    assert response.status_code == 400


def test_patch_monitor(client, api_headers, sample_monitor):
    response = client.patch(
        f"/api/monitors/{sample_monitor.id}",
        json={"enabled": False, "interval_seconds": 120},
        headers=api_headers,
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["enabled"] is False
    assert body["interval_seconds"] == 120


def test_delete_monitor(client, api_headers, sample_monitor):
    assert (
        client.delete(f"/api/monitors/{sample_monitor.id}", headers=api_headers).status_code == 204
    )
    assert client.get(f"/api/monitors/{sample_monitor.id}", headers=api_headers).status_code == 404


def test_immediate_check_endpoint(client, api_headers, http_server):
    created = client.post(
        "/api/monitors",
        json={"name": "Healthy", "url": f"{http_server}/ok", "interval_seconds": 60},
        headers=api_headers,
    ).get_json()
    response = client.post(f"/api/monitors/{created['id']}/check", headers=api_headers)
    assert response.status_code == 201
    body = response.get_json()
    assert body["check"]["success"] is True
    assert body["monitor"]["status"] == "up"


def test_immediate_check_reports_down(client, api_headers, http_server):
    created = client.post(
        "/api/monitors",
        json={"name": "Broken", "url": f"{http_server}/bad", "interval_seconds": 60},
        headers=api_headers,
    ).get_json()
    response = client.post(f"/api/monitors/{created['id']}/check", headers=api_headers)
    body = response.get_json()
    assert body["check"]["success"] is False
    assert body["monitor"]["status"] == "down"


def test_monitor_ownership_isolation(client, other_user, sample_monitor):
    headers = {"Authorization": f"Bearer {other_user.api_token}"}
    assert client.get(f"/api/monitors/{sample_monitor.id}", headers=headers).status_code == 404
    assert client.get("/api/monitors", headers=headers).get_json()["monitors"] == []


def test_checks_and_incidents_endpoints(client, api_headers, sample_monitor, db):
    record_check(sample_monitor, CheckResult(False, None, None, "boom"), failure_threshold=1)

    checks = client.get(f"/api/monitors/{sample_monitor.id}/checks", headers=api_headers)
    assert checks.status_code == 200
    assert len(checks.get_json()["checks"]) == 1

    incidents = client.get("/api/incidents", headers=api_headers)
    assert incidents.status_code == 200
    assert len(incidents.get_json()["incidents"]) == 1

    open_only = client.get("/api/incidents?status=open", headers=api_headers)
    assert len(open_only.get_json()["incidents"]) == 1

    resolved_only = client.get("/api/incidents?status=resolved", headers=api_headers)
    assert resolved_only.get_json()["incidents"] == []
