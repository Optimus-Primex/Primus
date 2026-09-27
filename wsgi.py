"""WSGI entrypoint for production servers (gunicorn/uwsgi)."""

from __future__ import annotations

import os

from primus import create_app

app = create_app(os.environ.get("PRIMUS_ENV", "production"))
