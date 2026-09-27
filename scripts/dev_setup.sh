#!/usr/bin/env bash
# Development bootstrap for Primus (Linux / macOS).
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements-dev.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — set PRIMUS_SECRET_KEY before deploying."
fi

export FLASK_APP=run.py
flask db upgrade

cat <<'EOF'
Setup complete.

Start the web app:   python run.py
Start the scheduler: flask primus worker
Optional demo data:  flask primus seed   (login: demo / demo-password)
EOF
