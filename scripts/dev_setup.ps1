# Development bootstrap for Primus (Windows PowerShell).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

python -m venv .venv
& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env - set PRIMUS_SECRET_KEY before deploying."
}

$env:FLASK_APP = "run.py"
python -m flask db upgrade

Write-Host ""
Write-Host "Setup complete."
Write-Host "Start the web app:   python run.py"
Write-Host "Start the scheduler: python -m flask primus worker"
Write-Host "Optional demo data:  python -m flask primus seed   (login: demo / demo-password)"
