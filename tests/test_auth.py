"""Authentication and account tests."""

from __future__ import annotations

from primus import create_app
from primus.models import User


def test_register_creates_user_and_signs_in(client, db):
    response = client.post(
        "/register",
        data={
            "username": "carol",
            "email": "carol@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 302
    assert User.query.filter_by(username="carol").count() == 1
    assert client.get("/").status_code == 200


def test_register_rejects_duplicate(client, user):
    response = client.post(
        "/register",
        data={
            "username": "alice",
            "email": "different@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 409


def test_register_rejects_weak_password(client):
    response = client.post(
        "/register",
        data={"username": "dave", "email": "dave@example.com", "password": "short"},
    )
    assert response.status_code == 400
    assert User.query.filter_by(username="dave").count() == 0


def test_login_with_invalid_password(client, user):
    response = client.post("/login", data={"identity": "alice", "password": "wrong"})
    assert response.status_code == 401


def test_login_with_email(client, user):
    response = client.post(
        "/login", data={"identity": "alice@example.com", "password": "password123"}
    )
    assert response.status_code == 302


def test_logout_clears_session(auth_client):
    assert auth_client.post("/logout").status_code == 302
    assert auth_client.get("/").status_code == 302


def test_account_requires_login(client):
    assert client.get("/account").status_code == 302


def test_rotate_token(auth_client, user, db):
    original = user.api_token
    assert auth_client.post("/account/token").status_code == 302
    db.session.expire_all()
    refreshed = User.query.filter_by(username="alice").one()
    assert refreshed.api_token != original


def test_registration_can_be_disabled():
    application = create_app("testing", {"PRIMUS_ALLOW_REGISTRATION": False})
    with application.app_context():
        from primus.extensions import db as app_db

        app_db.create_all()
        try:
            assert application.test_client().get("/register").status_code == 404
        finally:
            app_db.drop_all()
