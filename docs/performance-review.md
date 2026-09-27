# Performance Review

Scope: query behaviour and request latency of the dashboard and JSON API.

## Method

A synthetic dataset was generated (50 monitors × 100 checks) and the number of
SQL statements executed per request was counted with a SQLAlchemy
`before_cursor_execute` listener, timing `GET /` (dashboard) and
`GET /api/monitors`:

```
dashboard /            queries= 152  time=624.4ms     (before)
api /api/monitors      queries=  51  time= 95.7ms     (before)
```

## Finding: N+1 on uptime calculation (High) — fixed

`Monitor.uptime_percentage()` loaded up to 100 `Check` ORM objects per call. It
was invoked from `Monitor.to_dict()` (so listing N monitors issued N queries)
and **twice per row** in `templates/dashboard/index.html`, yielding up to
2N queries each transferring 100 rows.

**Fix (`primus/models.py`, `primus/dashboard/routes.py`, `primus/api/routes.py`,
`primus/templates/dashboard/index.html`):**

- `uptime_percentage()` now aggregates in SQL, transferring one row per monitor
  instead of up to 100 ORM objects.
- Added `Monitor.uptime_map(monitors)` which computes uptime for *all* monitors
  in a single window-function query.
- The dashboard precomputes the map and the template reads it once per row; the
  API list uses the same map, so `to_dict(uptime=...)` avoids a per-row query.

**After:**

```
dashboard /            queries=   3  time= 80.3ms
api /api/monitors      queries=   2  time= 21.8ms
```

That is roughly an **8× reduction in queries and latency** for the dashboard at
this size, and the cost no longer grows with the number of checks per monitor.

## Reviewed, no change needed

- **Indexes** already cover the hot paths: `ix_monitors_due
  (enabled, next_check_at)` for the scheduler, `ix_checks_monitor_checked
  (monitor_id, checked_at)` for history/uptime, and
  `ix_incidents_monitor_status (monitor_id, status)` for open-incident lookups.
- **Scheduler** claims due monitors by advancing `next_check_at` before the
  network call, so a crash cannot cause a hot loop, and work runs on a bounded
  thread pool.
- **Payload sizes** are bounded: check history and incident lists are limited by
  `PRIMUS_HISTORY_LIMIT` and capped at `PRIMUS_MAX_PAGE_SIZE`.

## Deliberately not done

Micro-optimisations (query caching layers, connection-pool tuning) were not
applied: there is no evidence they are needed at the current scale, and the
project's guidance is to avoid unjustified optimisation. They can be revisited
if a load test (`#95`) shows a real bottleneck.
