# Architecture

Primus is a single Python/Flask service with three entry surfaces (dashboard,
REST API, CLI) sharing one domain layer and one database.

```
                    ┌──────────────────────────────────────────┐
   Browser  ───────▶│  Dashboard (Jinja + vanilla JS/CSS)       │
                    └──────────────────────────────────────────┘
                                     │
   API client ─────▶  REST API  ─────┤  blueprints (primus/{dashboard,api,auth})
   (Bearer token)                    │
                    ┌────────────────┴───────────────┐
                    │  Services  (primus/services/)   │
                    │  • checker    HTTP + SSRF guard │
                    │  • incidents  state machine     │
                    │  • scheduler  due-monitor loop  │
                    │  • validators input validation  │
                    └────────────────┬───────────────┘
                                     │ SQLAlchemy ORM (primus/models.py)
                              ┌──────┴───────┐
                              │  Database    │  SQLite (default) / PostgreSQL
                              └──────────────┘
```

## Components

| Module                       | Responsibility                                                    |
| ---------------------------- | ----------------------------------------------------------------- |
| `primus/__init__.py`         | Application factory, blueprints, error handlers, security headers.|
| `primus/config.py`           | Environment-driven configuration per environment.                 |
| `primus/models.py`           | `User`, `Monitor`, `Check`, `Incident` and their relationships.   |
| `primus/services/checker.py` | Performs HTTP checks and classifies results (never raises).       |
| `primus/services/incidents.py`| Degree of failure tracking and incident open/resolve transitions.|
| `primus/services/scheduler.py`| Claims due monitors and dispatches checks to a thread pool.      |
| `primus/services/validators.py`| URL/payload validation and the SSRF guard.                      |
| `primus/api/`                | Token-authenticated JSON endpoints.                               |
| `primus/auth/`               | Registration, login, logout, account/API-token management.        |
| `primus/dashboard/`          | Server-rendered monitor management UI.                            |
| `primus/cli.py`              | `flask primus {init-db,create-user,seed,check-once,worker}`.      |

## Data model

```
users                         monitors                         checks
─────                         ────────                         ──────
id            PK              id            PK                 id           PK
username      UQ              user_id       FK -> users.id     monitor_id   FK
email         UQ              name                             success      bool
password_hash                 url                              status_code
api_token     UQ              method / expected_status         latency_ms
is_active                     timeout_seconds / interval_secs  error
created_at                    enabled                          checked_at
                              last_status / last_status_code
                              last_latency_ms / last_checked_at
                              next_check_at / consecutive_failures
                              created_at / updated_at

incidents
─────────
id            PK
monitor_id    FK -> monitors.id
status        open | resolved
cause
consecutive_failures
started_at / resolved_at
```

Relationships use `ON DELETE CASCADE` so deleting a monitor removes its history.
Indexes support the hot paths:

- `ix_monitors_due (enabled, next_check_at)` — the scheduler's due query.
- `ix_checks_monitor_checked (monitor_id, checked_at)` — history and uptime.
- `ix_incidents_monitor_status (monitor_id, status)` — open-incident lookups.

### Check lifecycle

1. The scheduler claims due monitors by advancing `next_check_at` *before* the
   network call, so a crash cannot cause a hot loop.
2. `checker.perform_check` issues the request (with a configurable timeout) and
   returns a `CheckResult`; failures are values, not exceptions.
3. `incidents.record_check` persists a `Check`, updates the monitor's
   denormalised "latest" fields, and applies the incident state machine.
4. Transitions that open or resolve an incident are returned as an
   `IncidentEvent`, which is the natural extension point for notifications.

## Key decisions

- **Normalised timestamps as naive UTC.** SQLite returns naive datetimes, so the
  codebase standardises on naive UTC via `models.utcnow()` to avoid aware/naive
  comparison bugs across databases.
- **Denormalised latest-check fields on `monitors`.** The dashboard renders many
  monitors per request; storing the latest status, code, and latency avoids an
  N+1 query. History remains in `checks`.
- **Injectable check function in the scheduler.** `Scheduler(check_func=...)`
  makes the scheduling logic unit-testable without network access, while
  production passes the real checker.
- **SQLite by default.** Zero-ops for single-node use. The ORM and migrations
  are database-agnostic, so PostgreSQL is a `PRIMUS_DATABASE_URL` away.
- **In-process scheduler by default, dedicated worker optional.** One process
  with the scheduler enabled is the simple path; `flask primus worker` allows
  web workers to scale independently.

## Scaling and operations

- To scale horizontally, run multiple web workers with
  `PRIMUS_ENABLE_SCHEDULER=0` and a single `flask primus worker`, and point
  `PRIMUS_DATABASE_URL` at PostgreSQL.
- `GET /api/health` performs a database round-trip and is used by the container
  health check.
- Gunicorn runs with a single worker and threads so the in-process scheduler
  runs exactly once (see `Dockerfile`).

## Known gaps and roadmap

These are real, unimplemented opportunities — not placeholders:

- **No alerting/notifications.** Incidents are recorded and shown in the UI, but
  nobody is notified. There is no delivery mechanism, no deduplication/cooldown,
  and no audit trail of notifications.
- **No retention policy.** `checks` grows unbounded; there is no pruning or
  roll-up of old data.
- **No public status page.** There is no read-only, unauthenticated view of
  monitor status to share with users.
- **Single-role accounts.** There are no organisations, roles, or permissions,
  and monitors are strictly per-user.
