"""WSGI entrypoint for production servers (gunicorn/uwsgi)."""

from __future__ import annotations

import atexit
import os

from primus import create_app
from primus.services.scheduler import start_scheduler_from_config

app = create_app(os.environ.get("PRIMUS_ENV", "production"))

# The container runs a single Gunicorn worker (see Dockerfile), so starting the
# in-process scheduler here is safe and keeps scheduled checks running under
# production servers, not just `python run.py`. Multi-worker deployments should
# set PRIMUS_ENABLE_SCHEDULER=0 and run `flask primus worker` instead.
_scheduler = start_scheduler_from_config(app)
if _scheduler is not None:
    atexit.register(_scheduler.stop)
