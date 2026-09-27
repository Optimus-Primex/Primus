# Contributing to Primus

Thanks for your interest in improving Primus! This document explains how to set
up a development environment and what we expect from contributions.

## Development setup

```bash
git clone https://github.com/Primex-Tech/Primus.git
cd Primus
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env
export FLASK_APP=run.py       # Windows PowerShell: $env:FLASK_APP="run.py"

flask db upgrade
flask primus seed
python run.py
```

Run the background scheduler alongside the web app when you need automatic
checks:

```bash
flask primus worker
```

## Branching

- Branch from `main`.
- Use a descriptive prefix: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`,
  `chore/`.
- Keep branches focused on a single change.

## Making changes

1. If you touch the schema, generate a migration:
   `flask db migrate -m "describe change"` and commit the generated file.
2. Keep business logic in `primus/services/`; keep blueprints thin.
3. Add or update tests under `tests/`. New behaviour without tests will not be
   merged.
4. Update the docs (`README.md`, `docs/`) when behaviour or configuration
   changes.

## Testing and quality gates

Before opening a pull request, all of the following must pass locally:

```bash
ruff check .
ruff format --check .
pytest
```

CI runs the same commands on Python 3.11 and 3.12, plus a migration check and a
Docker build.

## Pull requests

A good pull request includes:

- A short summary of the change and the problem it solves.
- The technical approach and any trade-offs.
- The commands you ran to validate the change and their results.
- Screenshots or a short recording for UI changes.
- A reference to the issue it closes (e.g. `Closes #123`).

## Commit messages

Use conventional, imperative commit messages, for example:

```
feat: add scheduled maintenance windows
fix: resolve incident on partial recovery
test: cover scheduler batch claiming
docs: document SSRF configuration
```

## Code style

- Formatting and import order are enforced by `ruff` (see `pyproject.toml`).
- Prefer small, composable functions and explicit error handling.
- Never commit secrets. `.env` and `instance/` are git-ignored — keep it that
  way.

## Reporting bugs

Open an issue that includes: what you expected, what happened, steps to
reproduce, and your environment (OS, Python version, database).
