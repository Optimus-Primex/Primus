"""Dashboard (server-rendered) tests."""

from __future__ import annotations

from primus.extensions import db as app_db
from primus.models import Monitor


def test_dashboard_requires_login(client):
    assert client.get("/").status_code == 302


def test_dashboard_lists_monitors(auth_client, sample_monitor):
    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"Example" in response.data


def test_dashboard_empty_state(auth_client):
    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"No monitors yet" in response.data


def test_create_monitor_via_form(auth_client, db):
    response = auth_client.post(
        "/monitors",
        data={
            "name": "New monitor",
            "url": "https://example.org",
            "method": "GET",
            "expected_status": "200",
            "timeout_seconds": "10",
            "interval_seconds": "300",
            "enabled": "on",
        },
    )
    assert response.status_code == 302
    assert Monitor.query.filter_by(name="New monitor").count() == 1


def test_create_monitor_rejects_bad_url(auth_client):
    response = auth_client.post("/monitors", data={"name": "Bad", "url": "not-a-url"})
    assert response.status_code == 400


def test_monitor_detail_page(auth_client, sample_monitor):
    response = auth_client.get(f"/monitors/{sample_monitor.id}")
    assert response.status_code == 200
    assert b"Recent checks" in response.data
    assert b"latencyChart" in response.data


def test_cannot_view_another_users_monitor(auth_client, other_user):
    monitor = Monitor(user_id=other_user.id, name="Secret", url="https://example.com")
    app_db.session.add(monitor)
    app_db.session.commit()
    assert auth_client.get(f"/monitors/{monitor.id}").status_code == 404


def test_toggle_and_delete_monitor(auth_client, sample_monitor, db):
    assert auth_client.post(f"/monitors/{sample_monitor.id}/toggle").status_code == 302
    db.session.expire_all()
    assert db.session.get(Monitor, sample_monitor.id).enabled is False

    assert auth_client.post(f"/monitors/{sample_monitor.id}/delete").status_code == 302
    assert db.session.get(Monitor, sample_monitor.id) is None
