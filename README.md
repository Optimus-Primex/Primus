# Primus

[![CI](https://github.com/Primex-Tech/Primus/actions/workflows/ci.yml/badge.svg)](https://github.com/Primex-Tech/Primus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

Primus is a self-hosted uptime and endpoint monitor. It periodically checks the
endpoints you care about — HTTP(S) services as well as **Stellar Horizon** and
**Soroban RPC** nodes — records the result, tracks uptime and latency over time,
and opens an **incident** when an endpoint starts failing.

It ships with a web dashboard, a token-authenticated REST API, a background
scheduler, a CLI, database migrations, a test suite, and CI — so you can run it
on a laptop, a VPS, or in a container without depending on a third-party SaaS.

## Why Primus?

Most uptime tools are either hosted services (your data lives elsewhere) or
heavy monitoring stacks. Primus targets the middle ground: a **small, readable,
single-service** monitor that you fully own. The whole application is a single
Python/Flask codebase you can audit in an afternoon.

## Features

- **HTTP(S) monitoring** with `GET`/`HEAD`, configurable timeout, expected
  status code, and interval.
- **Pluggable check types** — HTTP(S) by default, plus built-in **Stellar
  Horizon** (ledger lag), **Soroban RPC** (health + passphrase), **Soroban
  contract** event monitoring, and Stellar account/asset checks. See
  [`docs/stellar.md`](docs/stellar.md).
- **Status history** — every check is stored with status code, latency, and the
  error message when it fails.
- **Incident lifecycle** — an incident opens after N consecutive failures
  (configurable) and resolves automatically on recovery, with duration tracking.
- **Dashboard** — responsive server-rendered UI with summary cards, an uptime
  figure, a latency chart, recent checks, and incident history.
- **REST API** — manage monitors, run checks on demand, and read checks and
  incidents using a per-user bearer token.
- **Background scheduler** — an in-process worker, or a dedicated
  `flask primus worker` process for larger deployments.
- **Security defaults** — password hashing, CSRF protection on forms, per-user
  API tokens, an SSRF guard for outbound requests, strict security headers, and
  parameterised database access via SQLAlchemy.
- **Migrations & tests** — Flask-Migrate migrations and a pytest suite that
  covers the API, checker, incident state machine, and scheduler.

## Architecture

```
                    ┌──────────────────────────────────────────┐
   Browser  ───────▶│  Dashboard (Jinja templates + vanilla JS) │
                    └──────────────────────────────────────────┘
                                     │
   API client ─────▶  REST API  ─────┤   Flask application (primus/)
   (Bearer token)                    │
                    ┌────────────────┴───────────────┐
                    │  Services                      │
                    │  • checker  (HTTP + SSRF guard)│
                    │  • incidents (state machine)   │
                    │  • scheduler (background loop) │
                    └────────────────┬───────────────┘
                                     │ SQLAlchemy ORM
                              ┌──────┴───────┐
                              │  Database    │  SQLite (default) / PostgreSQL
                              └──────────────┘
```

See [`docs/architecture.md`](docs/architecture.md) for design decisions and the
data model.

## Technology

| Layer      | Choice                                  |
| ---------- | --------------------------------------- |
| Language   | Python 3.11+                            |
| Web        | Flask 3, Jinja2, vanilla JS/CSS         |
| Data       | SQLAlchemy 2, Flask-SQLAlchemy, Alembic |
| Auth       | Flask-Login sessions + bearer tokens    |
| Forms/CSRF | Flask-WTF / CSRFProtect                 |
| Server     | Gunicorn                                |
| Stellar    | Horizon REST + Soroban JSON-RPC (stdlib) |
| Contract   | Soroban (Rust, `soroban-sdk`)           |
| Tests/CI   | pytest, ruff, cargo test, GitHub Actions |
| Packaging  | Docker, docker-compose                  |

## Quick start

```bash
git clone https://github.com/Primex-Tech/Primus.git
cd Primus
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # then edit PRIMUS_SECRET_KEY
export FLASK_APP=run.py       # Windows PowerShell: $env:FLASK_APP="run.py"

flask db upgrade              # create the schema
flask primus seed             # optional demo user + monitors
flask primus worker &         # start the background checker
python run.py                 # start the web app on http://127.0.0.1:5000
```

Or with the helper scripts:

```bash
# Linux / macOS
./scripts/dev_setup.sh
# Windows PowerShell
./scripts/dev_setup.ps1
```

Then sign in. The seed command creates `demo` / `demo-password`; otherwise
register a new account at `/register`.

## Configuration

All configuration is read from environment variables (see `.env.example`).

| Variable                        | Default                 | Purpose                                         |
| ------------------------------- | ----------------------- | ----------------------------------------------- |
| `PRIMUS_ENV`                    | `development`           | `development`, `testing`, or `production`.      |
| `PRIMUS_SECRET_KEY`             | *(required in prod)*    | Session signing key.                            |
| `PRIMUS_DATABASE_URL`           | `sqlite:///dev.db`      | SQLAlchemy database URL.                        |
| `PRIMUS_ALLOW_REGISTRATION`     | `1`                     | Allow public sign-up.                           |
| `PRIMUS_ALLOW_PRIVATE_TARGETS`  | `0`                     | Disable the SSRF guard (monitor internal hosts).|
| `PRIMUS_ENABLE_SCHEDULER`       | `0` / `1` in `.env`     | Run the in-process scheduler.                   |
| `PRIMUS_FAILURE_THRESHOLD`      | `2`                     | Failures before an incident opens.              |
| `PRIMUS_MIN_INTERVAL`           | `30`                    | Minimum check interval in seconds.              |
| `PRIMUS_MAX_TIMEOUT`            | `60`                    | Maximum request timeout in seconds.             |
| `PRIMUS_CHECK_RETRIES`          | `1`                     | Retries per failed check.                       |
| `PRIMUS_COOKIE_SECURE`          | `0`                     | Set to `1` when serving over HTTPS.             |

## Running with Docker

```bash
export PRIMUS_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
docker compose up --build
# http://localhost:8000
```

## REST API

Authenticate with your account's API token (found on the **Account** page):

```bash
curl -H "Authorization: Bearer $PRIMUS_TOKEN" http://localhost:5000/api/monitors

curl -X POST http://localhost:5000/api/monitors \
  -H "Authorization: Bearer $PRIMUS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Example","url":"https://example.com","interval_seconds":300}'
```

Full reference: [`docs/api.md`](docs/api.md).

## Testing

```bash
pytest                       # run the suite
pytest --cov=primus          # with coverage
ruff check .                 # lint
ruff format --check .        # formatting
```

## Project structure

```
primus/
├── __init__.py          # application factory
├── config.py            # environment-driven configuration
├── extensions.py        # Flask extension singletons
├── models.py            # User, Monitor, Check, Incident
├── cli.py               # `flask primus ...` commands
├── api/                 # JSON REST API blueprint
├── auth/                # session auth blueprint
├── dashboard/           # server-rendered UI blueprint
├── services/            # checker, incidents, scheduler, validators
│   └── check_types/     # HTTP + Stellar/Soroban check-type plugins
├── templates/           # Jinja templates
└── static/              # CSS and vanilla JS
contracts/               # Soroban smart contracts (Rust)
migrations/              # Alembic / Flask-Migrate
tests/                   # pytest suite
docs/                    # architecture, API and Stellar docs
scripts/                 # developer setup helpers
```

## Stellar & Soroban

Primus can monitor Stellar Horizon endpoints, Soroban RPC nodes, Soroban smart
contracts, accounts, and assets — and it ships an on-chain Soroban registry
contract. See [`docs/stellar.md`](docs/stellar.md) for configuration and
examples, and [`contracts/primus-registry`](contracts/primus-registry) for the
contract.

## Contributing

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) first.

## Security

Please report vulnerabilities privately — see [`SECURITY.md`](SECURITY.md).

See [`docs/security-review.md`](docs/security-review.md) and
[`docs/performance-review.md`](docs/performance-review.md) for the latest
reviews (method, findings, fixes).

## License

[MIT](LICENSE) © 2026 Primex-Tech
