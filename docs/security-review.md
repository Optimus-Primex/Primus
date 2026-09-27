# Security Review

Scope: the entire `primus/` package and `requirements.txt`. Performed with a
manual code review plus two tools:

```bash
bandit -r primus
pip-audit -r requirements.txt
```

## Findings and fixes

### 1. Vulnerable pinned dependencies (Medium) — fixed

`pip-audit` reported 8 known advisories in 2 packages:

| Package  | Was     | Advisories                                  | Fixed in |
| -------- | ------- | ------------------------------------------- | -------- |
| Flask    | 3.1.1   | PYSEC-2026-2151                             | 3.1.3    |
| Werkzeug | 3.1.3   | PYSEC-2026-2046, PYSEC-2026-2044, PYSEC-2026-2320 | 3.1.6 |

**Fix:** bumped `Flask` to 3.1.3 and `Werkzeug` to 3.1.6 in
`requirements.txt`. `pip-audit` now reports *"No known vulnerabilities found"*.
A `security` job was added to CI (`.github/workflows/ci.yml`) running both
`pip-audit` and `bandit` on every push and pull request.

### 2. Unchecked URL schemes in the checker (B310, Medium) — fixed

`primus/services/checker.py` called `urllib.request.urlopen` without an explicit
scheme restriction at request time, so a value that bypassed creation-time
validation could theoretically request a non-HTTP scheme.

**Fix:** `perform_check` now parses the URL and rejects any scheme other than
`http`/`https` before opening it, in addition to the existing SSRF host check.
Bandit is satisfied with a justified `# nosec B310` on the call.

### 3. `assert` used for control flow (B101, Low) — fixed

`Scheduler.dispatch_due` used `assert self._executor is not None`, which is
stripped under `python -O`. Replaced with an explicit
`if executor is None: raise RuntimeError(...)` guard.

## Verified controls (no findings)

- **Secrets:** none hard-coded; configuration comes from environment variables,
  `.env` is git-ignored, and production refuses to start with the default secret
  key (`config.validate_production`).
- **Authorization:** every monitor/incident query is filtered by the owning
  `user_id`; the API requires a bearer token or an authenticated session.
- **Injection:** all database access goes through the SQLAlchemy ORM with bound
  parameters; there is no string-built SQL. Jinja auto-escapes templates and the
  CSP restricts `script-src` to `'self'` with no inline script.
- **SSRF:** `validators.validate_url` rejects non-HTTP(S), embedded credentials,
  control characters and whitespace; `assert_public_host` blocks private,
  loopback, link-local, reserved, multicast and unspecified addresses, and is
  re-checked at request time.
- **Passwords / sessions:** hashed with `werkzeug.security`; cookies are
  `HttpOnly`, `SameSite=Lax`, and `Secure` is configurable.
- **CSRF:** enabled on all form endpoints via Flask-WTF; the bearer-token API is
  exempt by design.
- **Headers:** `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
  and a restrictive `Content-Security-Policy` are set on every response.

## Residual risks / follow-ups

These are known, documented, and already tracked as issues — not overlooked:

- DNS-rebinding remains possible between validation and connection; hardening is
  tracked in **#67** (SSRF DNS pinning).
- Channel/check secrets are stored in the database; at-rest encryption is
  tracked in **#189**.
- Authentication rate limiting and email verification are tracked in **#59** and
  **#62**.
