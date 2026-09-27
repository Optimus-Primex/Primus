"""Authentication for the JSON API.

Two mechanisms are accepted:

* ``Authorization: Bearer <api_token>`` -- intended for machines.
* An authenticated browser session -- convenient for the dashboard.
"""

from __future__ import annotations

import functools

from flask import g, jsonify, request
from flask_login import current_user

from ..models import User


def authenticate() -> User | None:
    header = request.headers.get("Authorization", "")
    if header:
        scheme, _, token = header.partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return User.query.filter_by(api_token=token.strip()).first()
        return None
    if current_user.is_authenticated:
        return current_user
    return None


def api_auth_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        user = authenticate()
        if user is None or not user.is_active:
            return jsonify({"error": "authentication required"}), 401
        g.api_user = user
        return view(*args, **kwargs)

    return wrapped
