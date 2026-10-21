# Changelog

All notable changes to Primus are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-21

### Added

- Stellar/Soroban check types: Horizon ledger lag, Soroban RPC health,
  contract events, account balance and issued assets.
- `contracts/primus-registry`, a Soroban registry for monitor status, plus a
  Python `publish-status` command and an opt-in publish-after-check hook.
- Live testnet deployment of the registry with a verified `report` transaction.
- Redirect-aware SSRF protection: every redirect hop is re-validated.
- Tests for check types, the registry publisher, SSRF redirects and the
  scheduler (131 tests).

### Fixed

- The in-process scheduler now starts under Gunicorn/WSGI when enabled.
- Package discovery now includes the Stellar check-type plugins in wheels.
- `.env` files are loaded, and the placeholder user-agent URL was corrected.
- New `pip-audit` advisories in Werkzeug and python-dotenv were resolved.

### Documentation

- Canonical Optimus-Primex URLs, Stellar setup, registry deployment/publishing
  and updated security/performance notes.
