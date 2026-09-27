# REST API

Base URL: `/api`. All endpoints except `GET /api/health` require
authentication.

## Authentication

Send your API token (from the **Account** page) as a bearer token:

```
Authorization: Bearer <api_token>
```

An authenticated browser session is also accepted, which is what the dashboard
chart uses. Rotate your token from `/account`.

Errors are returned as JSON:

```json
{ "error": "monitor not found" }
```

| Status | Meaning                                          |
| ------ | ------------------------------------------------ |
| 200    | OK                                               |
| 201    | Created                                          |
| 204    | Deleted (no body)                                |
| 400    | Malformed request (e.g. body is not JSON)        |
| 401    | Missing or invalid credentials                   |
| 404    | Resource not found or not owned by you           |
| 422    | Validation failed (details in `error`)           |
| 503    | Health check failed (database unreachable)       |

## Endpoints

### `GET /api/health` — public

```json
{ "status": "ok", "database": true }
```

### `GET /api/monitors`

Returns `{"monitors": [ ... ]}`. A monitor object looks like:

```json
{
  "id": 1,
  "name": "Example",
  "url": "https://example.com",
  "method": "GET",
  "expected_status": 200,
  "timeout_seconds": 10,
  "interval_seconds": 300,
  "enabled": true,
  "status": "up",
  "last_status_code": 200,
  "last_latency_ms": 123.4,
  "last_checked_at": "2026-01-01T12:00:00+00:00",
  "next_check_at": "2026-01-01T12:05:00+00:00",
  "consecutive_failures": 0,
  "uptime_percentage": 99.5,
  "created_at": "...",
  "updated_at": "..."
}
```

### `POST /api/monitors`

Body (JSON):

| Field              | Required | Notes                                              |
| ------------------ | -------- | -------------------------------------------------- |
| `name`             | yes      | 1–120 characters.                                   |
| `url`              | yes      | `http`/`https`; private hosts blocked by default.  |
| `method`           | no       | `GET` (default) or `HEAD`.                          |
| `expected_status`  | no       | 100–599, default `200`.                             |
| `timeout_seconds`  | no       | 1–`PRIMUS_MAX_TIMEOUT`.                             |
| `interval_seconds` | no       | `PRIMUS_MIN_INTERVAL`–`PRIMUS_MAX_INTERVAL`.        |
| `enabled`          | no       | Boolean, default `true`.                            |

Returns `201` with the created monitor.

### `GET /api/monitors/{id}`

Returns the monitor, or `404`.

### `PATCH /api/monitors/{id}`

Partial update; accepts any subset of the create fields. Returns the updated
monitor.

### `DELETE /api/monitors/{id}`

Returns `204`. Deletes the monitor and all of its checks and incidents.

### `POST /api/monitors/{id}/check`

Runs a check immediately and returns:

```json
{
  "check": { "success": true, "status_code": 200, "latency_ms": 88.1, ... },
  "monitor": { "status": "up", ... },
  "event": "opened",
  "incident": { "status": "open", ... }
}
```

`event` and `incident` are only present when the check opened or resolved an
incident.

### `GET /api/monitors/{id}/checks?limit=N`

Returns `{"checks": [ ... ]}`, newest first. `limit` defaults to
`PRIMUS_HISTORY_LIMIT` and is capped at `PRIMUS_MAX_PAGE_SIZE`.

### `GET /api/monitors/{id}/incidents?limit=N`

Returns `{"incidents": [ ... ]}` for one monitor.

### `GET /api/incidents?status=open|resolved&limit=N`

Returns incidents across all of your monitors, optionally filtered by status.

## Example session

```bash
TOKEN=<your api token>
BASE=http://localhost:5000

# Create a monitor
curl -s -X POST "$BASE/api/monitors" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Example","url":"https://example.com","interval_seconds":300}'

# Check it now
curl -s -X POST "$BASE/api/monitors/1/check" -H "Authorization: Bearer $TOKEN"

# Read its history
curl -s "$BASE/api/monitors/1/checks?limit=20" -H "Authorization: Bearer $TOKEN"
```
