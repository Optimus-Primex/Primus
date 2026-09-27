"""Development/run entrypoint.

Run with::

    python run.py

For production use a WSGI server against ``wsgi:app`` (see the Dockerfile).
"""

from __future__ import annotations

import os

from primus import create_app
from primus.services.scheduler import start_scheduler_from_config

app = create_app()

if __name__ == "__main__":
    scheduler = start_scheduler_from_config(app)
    try:
        app.run(
            host=os.environ.get("PRIMUS_HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "5000")),
            debug=app.config.get("DEBUG", False),
        )
    finally:
        if scheduler is not None:
            scheduler.stop()
