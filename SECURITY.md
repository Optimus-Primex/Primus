# Security Policy

## Supported versions

Primus is pre-1.0. Security fixes are applied to the `main` branch.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, use GitHub's private vulnerability reporting (the **Security** tab →
**Report a vulnerability**) or email the maintainers. Include:

- A description of the issue and its impact.
- Steps to reproduce or a proof of concept.
- Affected versions and configuration.

We aim to acknowledge reports within a few days and to provide a remediation
timeline after triage.

## Security model

Primus makes outbound HTTP requests to user-supplied URLs, so it has two
important boundaries:

1. **SSRF protection.** `primus/services/validators.py` rejects non-HTTP(S)
   schemes, embedded credentials, control characters, and — unless
   `PRIMUS_ALLOW_PRIVATE_TARGETS=1` — hosts that resolve to private, loopback,
   link-local, reserved, multicast, or unspecified addresses. DNS is re-checked
   at request time in `primus/services/checker.py`. DNS-rebinding (TOCTOU)
   remains a residual risk; run Primus on a network where it cannot reach
   sensitive internal services, or disable private targets (the default).
2. **Authentication.** Browser sessions use Flask-Login with hashed passwords
   (`werkzeug.security`). The REST API authenticates with high-entropy per-user
   bearer tokens that can be rotated from the Account page. Cross-site request
   forgery is prevented on form endpoints by CSRFProtect; the token API is
   exempt because bearer tokens are not ambient credentials.

Additional hardening already in place:

- Parameterised queries through the ORM (no string-built SQL).
- `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a
  restrictive `Content-Security-Policy` are set on every response.
- Production refuses to boot with the default development secret key.
- Cookies are `HttpOnly` and `SameSite=Lax`; set `PRIMUS_COOKIE_SECURE=1` when
  serving over HTTPS.
