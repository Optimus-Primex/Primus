# Primus Backlog

Primus keeps a deliberately small **active** issue list. Everything else lives here so good ideas are not lost, but the contributor surface stays coherent. Deferred items are closed on GitHub and can be reopened when they become a priority.

_Active issues: 41 · Deferred ideas: 151._

## Active (near-term)

### Monitoring

- [#2](https://github.com/Primex-Tech/Primus/issues/2) — Support expected HTTP status ranges instead of a single code _(`medium`)
- [#3](https://github.com/Primex-Tech/Primus/issues/3) — Add response body assertions (contains / regex) to checks _(`medium`)
- [#4](https://github.com/Primex-Tech/Primus/issues/4) — Support per-monitor custom request headers _(`medium`)
- [#5](https://github.com/Primex-Tech/Primus/issues/5) — Add POST/PUT checks with a JSON request body _(`medium`)
- [#7](https://github.com/Primex-Tech/Primus/issues/7) — Add JSON-path assertions for API monitoring _(`hard`)
- [#8](https://github.com/Primex-Tech/Primus/issues/8) — Add tags/labels to monitors and filtering _(`medium`)
- [#15](https://github.com/Primex-Tech/Primus/issues/15) — Add TLS/SSL certificate expiry monitoring _(`hard`)
- [#16](https://github.com/Primex-Tech/Primus/issues/16) — Add TCP port monitoring _(`hard`)
- [#17](https://github.com/Primex-Tech/Primus/issues/17) — Add ICMP/ping monitoring _(`hard`)
- [#18](https://github.com/Primex-Tech/Primus/issues/18) — Add DNS record monitoring _(`hard`)
- [#19](https://github.com/Primex-Tech/Primus/issues/19) — Add multi-step HTTP transaction checks _(`hard`)
- [#25](https://github.com/Primex-Tech/Primus/issues/25) — Add configurable check result retention and pruning _(`medium`)
- [#102](https://github.com/Primex-Tech/Primus/issues/102) — Add composite monitors with dependencies _(`hard`)
- [#103](https://github.com/Primex-Tech/Primus/issues/103) — Add push/heartbeat (dead-man's switch) monitoring _(`hard`)
- [#106](https://github.com/Primex-Tech/Primus/issues/106) — Add configurable HTTP redirect policy to checks _(`medium`)

### Alerting

- [#1](https://github.com/Primex-Tech/Primus/issues/1) — Implement a pluggable alerting and notification subsystem _(`hard`)
- [#13](https://github.com/Primex-Tech/Primus/issues/13) — Add maintenance windows to suppress checks and alerts _(`hard`)
- [#21](https://github.com/Primex-Tech/Primus/issues/21) — Add anti-flapping / confirmation window for incidents _(`medium`)
- [#35](https://github.com/Primex-Tech/Primus/issues/35) — Add alert escalation policies _(`hard`)
- [#43](https://github.com/Primex-Tech/Primus/issues/43) — Provide a reference webhook receiver with signature verification _(`medium`)
- [#44](https://github.com/Primex-Tech/Primus/issues/44) — Add incident acknowledgement _(`medium`)
- [#46](https://github.com/Primex-Tech/Primus/issues/46) — Add incident severity levels _(`medium`)

### Reliability

- [#26](https://github.com/Primex-Tech/Primus/issues/26) — Add hourly/daily uptime rollups for long-term history _(`hard`)
- [#90](https://github.com/Primex-Tech/Primus/issues/90) — Add migration rollback tests _(`medium`)
- [#167](https://github.com/Primex-Tech/Primus/issues/167) — Verify models and migrations on PostgreSQL _(`medium`)
- [#169](https://github.com/Primex-Tech/Primus/issues/169) — Add a database lease for scheduler leadership _(`hard`)

### Security

- [#6](https://github.com/Primex-Tech/Primus/issues/6) — Add per-monitor HTTP authentication (Basic and Bearer) _(`hard`)
- [#59](https://github.com/Primex-Tech/Primus/issues/59) — Add rate limiting to login and registration _(`medium`)
- [#61](https://github.com/Primex-Tech/Primus/issues/61) — Add password reset via email _(`hard`)
- [#62](https://github.com/Primex-Tech/Primus/issues/62) — Add email verification on registration _(`hard`)
- [#67](https://github.com/Primex-Tech/Primus/issues/67) — Harden the SSRF guard with DNS pinning _(`hard`)
- [#70](https://github.com/Primex-Tech/Primus/issues/70) — Add dependency vulnerability scanning to CI _(`easy`)
- [#71](https://github.com/Primex-Tech/Primus/issues/71) — Add secret scanning to CI _(`easy`)
- [#72](https://github.com/Primex-Tech/Primus/issues/72) — Add automated tests for security headers _(`easy`)
- [#82](https://github.com/Primex-Tech/Primus/issues/82) — Add rate limiting for the API _(`medium`)
- [#189](https://github.com/Primex-Tech/Primus/issues/189) — Encrypt secret columns with an application key _(`hard`)

### Api

- [#74](https://github.com/Primex-Tech/Primus/issues/74) — Add cursor-based pagination to list endpoints _(`medium`)

### Observability

- [#78](https://github.com/Primex-Tech/Primus/issues/78) — Add request IDs and correlation to logs _(`medium`)
- [#79](https://github.com/Primex-Tech/Primus/issues/79) — Add optional structured JSON logging _(`medium`)
- [#80](https://github.com/Primex-Tech/Primus/issues/80) — Add a Prometheus /metrics endpoint _(`hard`)

### Testing

- [#91](https://github.com/Primex-Tech/Primus/issues/91) — Add a coverage gate to CI _(`easy`)

## Deferred

### Monitoring

- [#9](https://github.com/Primex-Tech/Primus/issues/9) — Add monitor groups/folders _(`hard`)
- [#10](https://github.com/Primex-Tech/Primus/issues/10) — Add bulk monitor actions (pause, enable, delete) _(`medium`)
- [#11](https://github.com/Primex-Tech/Primus/issues/11) — Add monitor cloning/duplication _(`—`)
- [#12](https://github.com/Primex-Tech/Primus/issues/12) — Import and export monitors as JSON/YAML _(`hard`)
- [#20](https://github.com/Primex-Tech/Primus/issues/20) — Add global and per-monitor uptime/SLA reporting _(`hard`)
- [#23](https://github.com/Primex-Tech/Primus/issues/23) — Add latency percentile metrics per monitor _(`medium`)
- [#24](https://github.com/Primex-Tech/Primus/issues/24) — Add HTTP method/endpoint to the health check for readiness vs liveness _(`easy`)
- [#51](https://github.com/Primex-Tech/Primus/issues/51) — Add a time-range selector to monitor detail _(`medium`)
- [#88](https://github.com/Primex-Tech/Primus/issues/88) — Add a dead-letter queue for permanently failed deliveries/checks _(`medium`)
- [#108](https://github.com/Primex-Tech/Primus/issues/108) — Support custom CA bundles and self-signed certificates _(`hard`)
- [#109](https://github.com/Primex-Tech/Primus/issues/109) — Add IPv4/IPv6 preference per monitor _(`medium`)
- [#110](https://github.com/Primex-Tech/Primus/issues/110) — Add active-hours scheduling windows per monitor _(`hard`)
- [#112](https://github.com/Primex-Tech/Primus/issues/112) — Add a monitor description/notes field _(`—`)
- [#113](https://github.com/Primex-Tech/Primus/issues/113) — Add owner/team contact metadata to monitors _(`medium`)
- [#116](https://github.com/Primex-Tech/Primus/issues/116) — Add full-text monitor search _(`medium`)
- [#117](https://github.com/Primex-Tech/Primus/issues/117) — Add per-user monitor quotas and limits _(`medium`)
- [#129](https://github.com/Primex-Tech/Primus/issues/129) — Capture screenshots on failed checks _(`hard`)
- [#130](https://github.com/Primex-Tech/Primus/issues/130) — Add an HTTP diagnostics panel for a check _(`hard`)
- [#131](https://github.com/Primex-Tech/Primus/issues/131) — Add a 'reproduce check with debug' action _(`medium`)
- [#132](https://github.com/Primex-Tech/Primus/issues/132) — Add response content hash change detection _(`hard`)
- [#133](https://github.com/Primex-Tech/Primus/issues/133) — Add a TLS certificate chain viewer _(`medium`)
- [#134](https://github.com/Primex-Tech/Primus/issues/134) — Add multi-resolver DNS propagation checks _(`hard`)
- [#136](https://github.com/Primex-Tech/Primus/issues/136) — Add probe health monitoring _(`medium`)
- [#137](https://github.com/Primex-Tech/Primus/issues/137) — Add geographic latency comparison _(`medium`)
- [#138](https://github.com/Primex-Tech/Primus/issues/138) — Add object-storage export of check history _(`hard`)
- [#145](https://github.com/Primex-Tech/Primus/issues/145) — Add adaptive check intervals _(`medium`)
- [#146](https://github.com/Primex-Tech/Primus/issues/146) — Add a priority and persistent check queue _(`hard`)
- [#172](https://github.com/Primex-Tech/Primus/issues/172) — Run browser tests in CI with failure artefacts _(`easy`)
- [#174](https://github.com/Primex-Tech/Primus/issues/174) — Add a load scenario for a large check batch _(`medium`)
- [#177](https://github.com/Primex-Tech/Primus/issues/177) — Add an optional headless-browser checker module _(`medium`)
- [#178](https://github.com/Primex-Tech/Primus/issues/178) — Add a browser monitor type with assertions _(`medium`)
- [#180](https://github.com/Primex-Tech/Primus/issues/180) — Add probe check assignment and result ingestion _(`hard`)
- [#181](https://github.com/Primex-Tech/Primus/issues/181) — Define the check-type plugin interface and loader _(`hard`)
- [#182](https://github.com/Primex-Tech/Primus/issues/182) — Add a sample check-type plugin and docs _(`medium`)
- [#187](https://github.com/Primex-Tech/Primus/issues/187) — Implement Terraform provider resource CRUD for monitors _(`hard`)

### Alerting

- [#14](https://github.com/Primex-Tech/Primus/issues/14) — Add per-monitor notification channel overrides _(`medium`)
- [#28](https://github.com/Primex-Tech/Primus/issues/28) — Add a Slack notification channel _(`medium`)
- [#29](https://github.com/Primex-Tech/Primus/issues/29) — Add a Discord notification channel _(`easy`)
- [#30](https://github.com/Primex-Tech/Primus/issues/30) — Add a Telegram notification channel _(`medium`)
- [#31](https://github.com/Primex-Tech/Primus/issues/31) — Add a Microsoft Teams notification channel _(`medium`)
- [#32](https://github.com/Primex-Tech/Primus/issues/32) — Add a PagerDuty notification channel _(`medium`)
- [#33](https://github.com/Primex-Tech/Primus/issues/33) — Add an SMS notification channel via Twilio _(`medium`)
- [#34](https://github.com/Primex-Tech/Primus/issues/34) — Add notification event filters (by severity, tag, or monitor) _(`hard`)
- [#36](https://github.com/Primex-Tech/Primus/issues/36) — Add on-call schedules _(`hard`)
- [#37](https://github.com/Primex-Tech/Primus/issues/37) — Add customisable notification message templates _(`medium`)
- [#38](https://github.com/Primex-Tech/Primus/issues/38) — Add recovery reminders and re-notification for long incidents _(`medium`)
- [#39](https://github.com/Primex-Tech/Primus/issues/39) — Add a scheduled daily/weekly digest report _(`medium`)
- [#40](https://github.com/Primex-Tech/Primus/issues/40) — Add per-channel quiet hours _(`medium`)
- [#41](https://github.com/Primex-Tech/Primus/issues/41) — Add a channel test action with delivery history _(`medium`)
- [#42](https://github.com/Primex-Tech/Primus/issues/42) — Document and version webhook payloads _(`easy`)
- [#45](https://github.com/Primex-Tech/Primus/issues/45) — Add an incident timeline with comments _(`hard`)
- [#47](https://github.com/Primex-Tech/Primus/issues/47) — Add manual incident creation and merging _(`medium`)
- [#48](https://github.com/Primex-Tech/Primus/issues/48) — Add CSV/JSON export of checks and incidents _(`medium`)
- [#104](https://github.com/Primex-Tech/Primus/issues/104) — Add status page incident history and email subscriptions _(`hard`)
- [#105](https://github.com/Primex-Tech/Primus/issues/105) — Add response-time SLA budgets with breach alerts _(`medium`)
- [#124](https://github.com/Primex-Tech/Primus/issues/124) — Add per-channel retry policies _(`medium`)
- [#125](https://github.com/Primex-Tech/Primus/issues/125) — Add alert storm suppression _(`hard`)
- [#126](https://github.com/Primex-Tech/Primus/issues/126) — Add incident postmortem templates and export _(`medium`)
- [#127](https://github.com/Primex-Tech/Primus/issues/127) — Add incident MTTR/MTBF metrics _(`medium`)
- [#183](https://github.com/Primex-Tech/Primus/issues/183) — Define the notification-channel plugin interface and loader _(`hard`)
- [#184](https://github.com/Primex-Tech/Primus/issues/184) — Add a sample notification-channel plugin _(`medium`)

### Reliability

- [#22](https://github.com/Primex-Tech/Primus/issues/22) — Add request jitter to the scheduler to avoid thundering herd _(`easy`)
- [#27](https://github.com/Primex-Tech/Primus/issues/27) — Add database backup and restore CLI commands _(`medium`)
- [#87](https://github.com/Primex-Tech/Primus/issues/87) — Add graceful shutdown draining to the scheduler _(`medium`)
- [#147](https://github.com/Primex-Tech/Primus/issues/147) — Add DST- and timezone-correct scheduling tests _(`medium`)
- [#170](https://github.com/Primex-Tech/Primus/issues/170) — Test scheduler failover between instances _(`medium`)
- [#186](https://github.com/Primex-Tech/Primus/issues/186) — Implement idempotent apply with dry-run and pruning _(`hard`)

### Security

- [#60](https://github.com/Primex-Tech/Primus/issues/60) — Add account lockout after repeated failed logins _(`medium`)
- [#68](https://github.com/Primex-Tech/Primus/issues/68) — Replace inline-style CSP allowance with nonces _(`medium`)
- [#69](https://github.com/Primex-Tech/Primus/issues/69) — Add trusted proxy and HSTS configuration _(`medium`)
- [#107](https://github.com/Primex-Tech/Primus/issues/107) — Add proxy support for outbound checks _(`hard`)
- [#111](https://github.com/Primex-Tech/Primus/issues/111) — Add per-target politeness rate limiting _(`medium`)
- [#120](https://github.com/Primex-Tech/Primus/issues/120) — Add team invitations and member management _(`hard`)
- [#121](https://github.com/Primex-Tech/Primus/issues/121) — Enforce and test organisation data isolation _(`hard`)
- [#123](https://github.com/Primex-Tech/Primus/issues/123) — Add service accounts distinct from human users _(`medium`)
- [#139](https://github.com/Primex-Tech/Primus/issues/139) — Add GDPR data export and deletion _(`hard`)
- [#148](https://github.com/Primex-Tech/Primus/issues/148) — Add mTLS client certificate support for checks _(`hard`)
- [#149](https://github.com/Primex-Tech/Primus/issues/149) — Add OAuth2 client-credentials support for checks _(`hard`)
- [#152](https://github.com/Primex-Tech/Primus/issues/152) — Add Organization and Membership models _(`medium`)
- [#153](https://github.com/Primex-Tech/Primus/issues/153) — Scope monitors and channels to the active organization _(`hard`)
- [#154](https://github.com/Primex-Tech/Primus/issues/154) — Migrate existing accounts to a personal organization _(`medium`)
- [#155](https://github.com/Primex-Tech/Primus/issues/155) — Define roles and a permission matrix _(`easy`)
- [#156](https://github.com/Primex-Tech/Primus/issues/156) — Enforce role permissions across API and dashboard routes _(`medium`)
- [#157](https://github.com/Primex-Tech/Primus/issues/157) — Add OIDC configuration and authorization-code flow _(`hard`)
- [#158](https://github.com/Primex-Tech/Primus/issues/158) — Map OIDC claims to users and link accounts _(`hard`)
- [#159](https://github.com/Primex-Tech/Primus/issues/159) — Add TOTP enrolment and recovery codes _(`medium`)
- [#160](https://github.com/Primex-Tech/Primus/issues/160) — Require the second factor at login _(`medium`)
- [#161](https://github.com/Primex-Tech/Primus/issues/161) — Track and list active sessions _(`medium`)
- [#162](https://github.com/Primex-Tech/Primus/issues/162) — Allow revoking individual or all sessions _(`easy`)
- [#163](https://github.com/Primex-Tech/Primus/issues/163) — Add multiple named API tokens with scopes _(`medium`)
- [#164](https://github.com/Primex-Tech/Primus/issues/164) — Enforce token scopes and expiry on API routes _(`medium`)
- [#165](https://github.com/Primex-Tech/Primus/issues/165) — Add an audit log model and write sensitive events _(`medium`)
- [#166](https://github.com/Primex-Tech/Primus/issues/166) — Expose a read-only audit log view _(`easy`)
- [#179](https://github.com/Primex-Tech/Primus/issues/179) — Add probe registration and authentication _(`hard`)
- [#190](https://github.com/Primex-Tech/Primus/issues/190) — Add key rotation for encrypted secrets _(`medium`)
- [#191](https://github.com/Primex-Tech/Primus/issues/191) — Add a secrets-backend interface with local fallback _(`medium`)
- [#192](https://github.com/Primex-Tech/Primus/issues/192) — Add a secrets-manager backend and tests _(`medium`)

### Api

- [#75](https://github.com/Primex-Tech/Primus/issues/75) — Version the REST API under /api/v1 _(`medium`)
- [#77](https://github.com/Primex-Tech/Primus/issues/77) — Add ETag/conditional request support for read endpoints _(`medium`)
- [#83](https://github.com/Primex-Tech/Primus/issues/83) — Document an API error catalogue _(`medium`)
- [#84](https://github.com/Primex-Tech/Primus/issues/84) — Publish a Python client SDK _(`hard`)

### Ui

- [#49](https://github.com/Primex-Tech/Primus/issues/49) — Add a public read-only status page _(`hard`)
- [#50](https://github.com/Primex-Tech/Primus/issues/50) — Add an embeddable SVG status badge endpoint _(`medium`)
- [#52](https://github.com/Primex-Tech/Primus/issues/52) — Add interactive charts with tooltips and zoom _(`—`)
- [#53](https://github.com/Primex-Tech/Primus/issues/53) — Add a dark mode theme _(`easy`)
- [#55](https://github.com/Primex-Tech/Primus/issues/55) — Add live auto-refresh to the dashboard _(`medium`)
- [#56](https://github.com/Primex-Tech/Primus/issues/56) — Add loading skeletons and optimistic UI _(`—`)
- [#57](https://github.com/Primex-Tech/Primus/issues/57) — Add an internationalisation (i18n) framework _(`hard`)
- [#58](https://github.com/Primex-Tech/Primus/issues/58) — Add progressive web app (PWA) support _(`medium`)
- [#76](https://github.com/Primex-Tech/Primus/issues/76) — Add filtering and sorting query parameters to list endpoints _(`medium`)
- [#114](https://github.com/Primex-Tech/Primus/issues/114) — Add favourites and pinning to the dashboard _(`—`)
- [#115](https://github.com/Primex-Tech/Primus/issues/115) — Add saved filters and views to the dashboard _(`medium`)

### Testing

- [#54](https://github.com/Primex-Tech/Primus/issues/54) — Improve accessibility and add automated a11y tests _(`medium`)
- [#92](https://github.com/Primex-Tech/Primus/issues/92) — Add property-based tests for validators using Hypothesis _(`medium`)
- [#93](https://github.com/Primex-Tech/Primus/issues/93) — Add mutation testing configuration _(`medium`)
- [#96](https://github.com/Primex-Tech/Primus/issues/96) — Add API contract tests _(`medium`)
- [#171](https://github.com/Primex-Tech/Primus/issues/171) — Add a Playwright test harness with core flows _(`medium`)
- [#173](https://github.com/Primex-Tech/Primus/issues/173) — Add a load scenario for API reads _(`medium`)

### Infrastructure

- [#73](https://github.com/Primex-Tech/Primus/issues/73) — Add an OpenAPI specification and generated docs _(`hard`)
- [#81](https://github.com/Primex-Tech/Primus/issues/81) — Add OpenTelemetry tracing _(`hard`)
- [#97](https://github.com/Primex-Tech/Primus/issues/97) — Optimise the Docker image with a multi-stage build _(`medium`)
- [#99](https://github.com/Primex-Tech/Primus/issues/99) — Add release automation and a changelog _(`medium`)
- [#100](https://github.com/Primex-Tech/Primus/issues/100) — Add Dependabot with safe auto-merge for patch updates _(`medium`)
- [#101](https://github.com/Primex-Tech/Primus/issues/101) — Add a contributor dev container _(`medium`)
- [#144](https://github.com/Primex-Tech/Primus/issues/144) — Add systemd unit files and a deployment guide _(`medium`)
- [#168](https://github.com/Primex-Tech/Primus/issues/168) — Add a PostgreSQL job to CI _(`easy`)
- [#175](https://github.com/Primex-Tech/Primus/issues/175) — Add Kubernetes manifests for web and worker _(`medium`)
- [#176](https://github.com/Primex-Tech/Primus/issues/176) — Add a Helm chart with values and docs _(`medium`)
- [#185](https://github.com/Primex-Tech/Primus/issues/185) — Add a declarative monitor/channel file schema and parser _(`medium`)
- [#188](https://github.com/Primex-Tech/Primus/issues/188) — Add a Terraform provider data source and docs _(`medium`)

### Epics (split into children)

- [#63](https://github.com/Primex-Tech/Primus/issues/63) — Add TOTP two-factor authentication _(`—`)
- [#64](https://github.com/Primex-Tech/Primus/issues/64) — Add an active sessions list with revocation _(`—`)
- [#65](https://github.com/Primex-Tech/Primus/issues/65) — Add scoped API tokens _(`—`)
- [#66](https://github.com/Primex-Tech/Primus/issues/66) — Add a security audit log _(`—`)
- [#85](https://github.com/Primex-Tech/Primus/issues/85) — Add first-class PostgreSQL support and a CI matrix job _(`—`)
- [#86](https://github.com/Primex-Tech/Primus/issues/86) — Add scheduler leader election for multi-worker deployments _(`—`)
- [#94](https://github.com/Primex-Tech/Primus/issues/94) — Add end-to-end browser tests with Playwright _(`—`)
- [#95](https://github.com/Primex-Tech/Primus/issues/95) — Add a load/performance test harness _(`—`)
- [#98](https://github.com/Primex-Tech/Primus/issues/98) — Add Kubernetes manifests and a Helm chart _(`—`)
- [#118](https://github.com/Primex-Tech/Primus/issues/118) — Add organisations/teams for multi-tenancy _(`—`)
- [#119](https://github.com/Primex-Tech/Primus/issues/119) — Add role-based access control _(`—`)
- [#122](https://github.com/Primex-Tech/Primus/issues/122) — Add SSO/OIDC login _(`—`)
- [#128](https://github.com/Primex-Tech/Primus/issues/128) — Add synthetic browser (headless) monitoring _(`—`)
- [#135](https://github.com/Primex-Tech/Primus/issues/135) — Add distributed probe agents _(`—`)
- [#140](https://github.com/Primex-Tech/Primus/issues/140) — Add a plugin system for check types _(`—`)
- [#141](https://github.com/Primex-Tech/Primus/issues/141) — Add a plugin system for notification channels _(`—`)
- [#142](https://github.com/Primex-Tech/Primus/issues/142) — Add declarative config-as-code monitor sync _(`—`)
- [#143](https://github.com/Primex-Tech/Primus/issues/143) — Add a Terraform provider _(`—`)
- [#150](https://github.com/Primex-Tech/Primus/issues/150) — Add encryption at rest for stored secrets with key rotation _(`—`)
- [#151](https://github.com/Primex-Tech/Primus/issues/151) — Add an external secrets manager integration _(`—`)

### (Unlabelled)

- [#89](https://github.com/Primex-Tech/Primus/issues/89) — Improve the seed/demo data generator _(`—`)

