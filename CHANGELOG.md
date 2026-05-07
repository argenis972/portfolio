# 📊 CHANGELOG

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) with semantic versioning.

This changelog separates three categories intentionally:
- 🔥 **Production Incidents** — events that affected real system behavior
- 🚀 **Releases** — versioned feature and improvement history
- 🔧 **Hardening** — internal improvements with no direct user impact

---

## 🔥 Production Incidents

> Incidents are documented separately from releases because they represent real system behavior under failure — not planned work.

---

### INC-001 · Rate Limiter Silently Disabled in Production
**Period**: v1.2.0 → v1.3.0 (approximately 2 weeks)
**Affected**: `POST /api/v1/contact` — anti-spam protection

**What happened**
The `/contact` endpoint had rate limiting configured via `slowapi` with in-memory storage. Tests passed. Staging passed. In production on Koyeb, the free tier restarts containers on inactivity, redeploys, and occasionally without visible reason. Every restart zeroed the in-memory counters. The anti-spam protection was effectively non-functional in production — a user could bypass the limit by waiting for a natural container cycle, which happened every few hours.

**How it was discovered**
Not by an alert. Discovered manually during a routine test of the contact endpoint the day after a redeploy, when the rate limit counter had clearly reset.

**What was tried first (didn't work)**
Increased the in-memory TTL to 24 hours. This only masked the symptom — the counter still zeroed on any restart, regardless of TTL.

**Root cause**
Koyeb free tier ephemeral containers. Any in-memory state is container-local and not persisted across the container lifecycle.

**Resolution (v1.3.0)**
Migrated rate limiting storage to Redis (Upstash). Counters now survive container restarts and are consistent across replicas.

**Accepted side effect**
Redis is now in the critical path for `/contact`. If Upstash is unavailable, the rate limiter fails open — requests pass through unthrottled. This failure mode is documented and accepted (failing closed would block legitimate contact attempts during an infrastructure outage).

---

### INC-002 · Cold Start Latency Making Keep-Alive Useless
**Period**: v1.2.0 → v1.4.1
**Affected**: First real request after Koyeb container sleep

**What happened**
A cron-based keep-alive pinged `/health` every 14 minutes to prevent Koyeb from sleeping the container. The strategy worked — the container stayed warm. However, P95 on the first *portfolio data* request after sleep was still 280–400ms. The keep-alive was hitting `/health`, but the actual slow path was the PostgreSQL connection being re-established for the data endpoints.

**What was tried first (didn't work)**
Reducing the keep-alive interval to 10 minutes. The container stayed awake, but the latency problem persisted. The bottleneck was not sleep — it was the Supabase connection overhead on every cold data read, regardless of whether the container was warm.

**Root cause**
Static portfolio data (projects, about, stack) was being served from PostgreSQL. Every read required a connection round-trip to Supabase, adding 200–350ms to the response time.

**Resolution (ADR-05 + v1.4.1)**
Migrated all static portfolio reads to `JSONRepository` — files loaded into memory at startup. PostgreSQL now only handles transactional data (contact submissions, chaos records). P95 on data reads dropped from ~320ms to <50ms.

**Accepted side effect**
Updating portfolio content now requires a container redeploy, not a database update. This is intentional.

---

### INC-003 · Chaos Playground Crashing on Database Unavailability
**Period**: v1.4.x
**Affected**: Entire Chaos Playground UI

**What happened**
The Chaos Playground simulates failures and records each incident to PostgreSQL. During a brief Supabase connectivity issue, the database write raised an unhandled exception that propagated up through the entire chaos action handler. The playground crashed completely — not because the simulation failed, but because a *secondary* operation (recording the incident) failed.

**The irony**
A tool designed to demonstrate failure resilience was itself not resilient to a single downstream failure.

**Resolution (ADR-14)**
Wrapped all chaos persistence calls in try/except. Database write failures are logged but do not interrupt the simulation. The playground now completes its primary job (running the simulation) even when its secondary job (recording to DB) fails.

**Accepted side effect**
Incidents that occur during a database outage are silently lost from the history panel. Acceptable — this is a demo tool, not a production incident recorder.

---

### INC-004 · CSP Blocking Frontend ↔ Backend Communication in Production
**Period**: v1.3.x → v1.4.0
**Affected**: All API calls from the deployed frontend

**What happened**
After setting up the custom domain `argenisbackend.com`, the Vercel-deployed frontend started blocking its own API calls in production. The browser console showed CSP violations: the Content Security Policy on the frontend didn't include `api.argenisbackend.com` as an allowed `connect-src`. All API requests were blocked at the browser level.

**Why it wasn't caught earlier**
Development used `localhost`. Staging used the Vercel preview URL, which had a different CSP config. The production CSP was only applied after the custom domain was configured — the first time anyone tested the full production path.

**Root cause**
CSP in `vercel.json` had not been updated to include the production API subdomain. Vercel and Koyeb each managed their own security headers independently, with no single source of truth.

**Resolution (ADR-15.3)**
CSP in `vercel.json` explicitly whitelists `api.argenisbackend.com`. CORS regex in `settings.py` covers the corresponding origin. Both are now updated together — separate changes to either without the other will cause this failure to recur.

---

### INC-005 · Monorepo Build Context Mismatch (Deployment Blocker)
**Period**: v1.6.0 (Current session)
**Affected**: CI/CD Pipeline & Deployment (Koyeb + GitHub Actions)

**What happened**
Deployments started failing on Koyeb with `file not found` errors for `requirements.txt` and `app/`. Fixing it for Koyeb (by building from root) broke GitHub Actions, which was configured to build from inside the `/backend` directory.

**What was tried first (didn't work)**
We tried to force the "Work Directory" to `/backend` in the Koyeb service configuration. This not only failed to fix the build but **made things worse** by creating an absolute discrepancy between the Dockerfile context and the runner's actual filesystem, making local and CI paths completely incompatible.

**Root cause**
Inconsistent Docker build contexts across environments. The `Dockerfile` used relative paths that were context-dependent.

**Resolution**
Standardized the build context to the **repository root** for all environments. Updated the `Dockerfile` to use prefixed paths (`COPY backend/requirements.txt`) and modified the GitHub Action to point to the root context with `-f backend/Dockerfile .`.

**Accepted side effect**
Local builds now also require being run from the repository root.

---

### INC-006 · Spam Filter False Positive on Mixed-Protocol Links
**Period**: v1.7.0 (antispam enhancement) → v1.8.0
**Affected**: `POST /api/v1/contact` — spam scoring Rule 2 (excessive links penalty)

**What happened**
The antispam filter incorrectly penalized legitimate messages containing one `https://` URL and one bare `www.` URL pointing to **different** domains. The filter counted them as "2 links to 1 unique domain" and applied an extra +15 spam score, pushing some legitimate multi-link messages into the SUSPECT tier.

**How it was discovered**
Static analysis by an automated code review bot. No user complaints received — but the failure mode was systematically biased against any message linking to two different sites when one used a bare `www.` prefix.

**Root cause**
`all_links` used `re.findall(r"https?://|www\.")` — capturing protocol/prefix *patterns*, not full URL tokens. `unique_domains` used a separate regex that only processed `https://` URLs. The two variables were not measuring the same thing.

**Resolution (v1.8.0)**
Unified extraction: both regexes replaced with a single `re.findall(r"https?://[^\s]+|www\.[^\s]+")` that captures full URL tokens. Normalization now strips protocol prefixes, `www.`, and trailing prose punctuation. Three regression tests added to `test_spam.py` cover the corrected behavior.

**Accepted side effect**
None. The fix is strictly more accurate.

---

### INC-007 · Koyeb Terraform Provider Schema Incompatibility
**Period**: v1.7.0 → v1.8.1
**Affected**: Infrastructure Provisioning CI/CD

**What happened**
The migration to Terraform was blocked by a `400 Bad Request` from the Koyeb API: `env type is required`. The official Terraform provider (v0.1.11) lacked the schema fields to send this mandatory metadata, making the standard `env` block unusable for literal values.

**Root cause**
A version mismatch between a stagnant provider (last updated 2024) and an evolving API (2026 requirements).

**Resolution (v1.8.1)**
Implemented **Secret-First Orchestration**. Every environment variable was moved to a `koyeb_secret` resource. The service definition was refactored to use `secret` references instead of `value` keys. Since secret references in the Koyeb API have an implicit type, this bypassed the provider's schema limitation.

**Accepted side effect**
All configuration variables are now treated as secrets in the Koyeb UI, which actually improves the overall security posture (SRE best practice).

---

### INC-008 · Destructive IaC Migration (Free Tier Constraints)
**Period**: v1.7.1 → v1.8.1 (Migration Window)
**Affected**: Global API Availability (`api.argenisbackend.com`)
**Downtime**: 14 hours

**What happened**
To finalize the transition to IaC, the existing manual infrastructure was decommissioned. Due to Koyeb Free Tier limitations (1-service limit and strict domain exclusivity), a zero-downtime migration was impossible. The system underwent a "Cold Migration" to ensure 100% operational consistency and reproducibility.

**Root cause**
Koyeb prevented Terraform from claiming the custom domain while the legacy manual service still held the CNAME hook. Provider ownership constraints forced a "Delete-before-Create" strategy.

**Resolution**
Full infrastructure wipe followed by a clean Terraform provision. This verified that the entire stack is now 100% reproducible from code, eliminating all "shadow configuration" and unmanaged resources.

**Lessons Learned**
*   **Infrastructure Consistency over Uptime**: In restricted environments, maintenance windows are a necessary trade-off for long-term reproducibility.
*   **Reconciliation Tax**: Migrating unmanaged infrastructure into IaC may require destructive reconciliation steps when provider ownership cannot be safely imported.

---

## [1.8.1] - 2026-05-07

### IaC Automation & Regional Migration

> This release marks the full transition to Infrastructure as Code (IaC). We automated the entire backend provisioning using Terraform, resolved a critical provider-level failure through architectural adaptation, and optimized the system's physical location for better latency.

#### Added
- **Full Terraform Automation**: Managed provisioning of Koyeb App, Service, Domain, and Secrets Vault.
- **Secret-First Orchestration (INC-007)**: Workaround for provider schema limitations by vaulting all environment variables as secrets.
- **Resilient Provisioning**: Terraform logic that automatically filters missing optional secrets to prevent deployment locks.

#### Changed
- **Regional Migration**: Moved the production backend from `fra` (Frankfurt) to `was` (Washington D.C.) to co-locate with the database and reduce cross-region latency.
- **HCP Terraform Context**: Switched to Local Execution Mode to allow secure secret injection from GitHub Actions runners.

#### Fixed
- **Domain Identity Assignment**: Fixed a missing link between the custom domain and the application in the Terraform configuration.

---

## [1.8.0] - 2026-05-05

### Visual Consistency & System Closure

> The objective of this release is to finalize the portfolio's presentation and stability. We applied strict visual consistency to the typography and design system tokens, and patched a critical edge case in the anti-spam system before final delivery.

#### Fixed
- **Spam Filter Accuracy (INC-006)**: Unified URL extraction logic to prevent false positives when users submitted mixed-protocol links (e.g., `https://` + `www.`). Normalization now strips trailing prose punctuation.
- **Heading Hierarchy Consistency**: Extended the `Montserrat` font application in `index.css` to cover `h4` and `h5` elements, ensuring uniform typography across all nested sections (e.g., incident timelines).
- **Design System Drift**: Replaced isolated hardcoded color classes (`from-white`, `text-slate-500`) in `FeaturedIncident` and `Projects` with native theme-aware tokens (`text-app-text`, `text-app-muted`).

#### Changed
- Removed leftover internal development scripts (`fix_db.py`, `scratch_rename.py`) to enforce a clean project root.

---

## [1.7.0] - 2026-05-04

### Final Professionalization & SRE Evidence

> The objective of this release is to complete the final phase of the SRE portfolio by implementing high-impact reliability and operational improvements. The repository now serves as a professional-grade technical narrative.

#### Added
- **Minimum Viable IaC**: Introduced Terraform provisioning in `infrastructure/` focused on the Koyeb backend service. Purposefully scoped to avoid over-engineering external stateful services. See ADR-18.
- **Chaos E2E CI Testing**: Added a weekly GitHub Actions workflow that spins up a local `docker-compose` environment and runs narrative E2E tests against the Chaos Playground endpoints. Ensures the system actually degrades and recovers as advertised. See ADR-17.
- **Fail-Silent Health Check**: Modified the `/health` endpoint to return `200 OK (Degraded)` instead of `503` when database dependencies fail. This prevents orchestrator restarts from breaking the fail-silent caching layer.
- **Security Visibility**: Restructured `README.md` to prominently highlight security decisions and architectural tradeoffs right at the top.

---

## [1.6.0] - 2026-04-22

### Full Structural Refactor & Build Standardization

> The monolithic `api.ts` had grown to the point where adding a new endpoint meant scrolling through 400 lines of mixed schema definitions, fetch logic, and type exports. The Dockerfile was failing on every CI run because the build context differed between local, GitHub Actions, and Koyeb. Both problems were about the same thing: the codebase had grown past its original structure.

#### Added
- **Modular frontend API layer** (`src/api/`): Split into `client`, `schemas`, and service modules per domain (`portfolio`, `chaos`). Each module has a single responsibility and can be tested independently.
- **`ChaosTerminal` and `ChaosActionCard` components**: Extracted from the monolithic `ChaosPlayground.tsx`. The original component was handling rendering, state, API calls, and animation simultaneously.
- **`useCurrentTime` hook**: Replaced direct `Date.now()` calls scattered across components with a single reactive time source. This fixed a React hook purity violation where `Date.now()` inside render was producing different values per render cycle.

#### Fixed
- **Dockerfile build context**: The Dockerfile now builds from the repository root with explicit path prefixes (`COPY backend/requirements.txt`). Previously, local builds worked (context was `backend/`) but CI failed (context was `/`). See ADR-15.
- **CSP / CORS domain sync**: `api.argenisbackend.com` whitelisted in both `vercel.json` (CSP) and `settings.py` (CORS). See INC-004.
- **Chaos persistence crash**: Fail-silent pattern in `chaos.py`. See INC-003.

#### Migration note
All frontend Zod schemas and TypeScript interfaces updated to match English backend field names from the v1.4.1 migration. Any schema mismatch will surface as a runtime Zod parse error — check the browser console if API data isn't rendering.

---

## [1.5.1] - 2026-04-21

### Honest Telemetry Labeling

> The dashboard was showing a continuous, smooth telemetry line. A reviewer pointed out it was unclear which data points were measured from the backend and which were interpolated between polls. The unlabeled mix was misleading — it implied higher measurement frequency than actually exists.

#### Added
- **Synthetic vs. real telemetry labels**: Dashboard now distinguishes `backend` samples (confirmed by API) from `synthetic` samples (frontend interpolation between polls). Synthetic segments render as dashed violet lines with an explicit badge. See ADR-13.
- **Confidence indicator**: Shows what percentage of the current view is backend-confirmed data.
- **Project case study structure**: Projects now render with Problem, Constraint, Decision, Trade-off, Impact, and Stack fields. Previously, project descriptions were prose paragraphs with no queryable structure.
- **Engineering timeline**: Experience and education render as a vertical timeline organized around decision, failure, learning, and impact — not job titles and date ranges.

#### Modified
- **Telemetry sparkline**: Shortened visible window, added average baseline, differentiated synthetic segments visually.
- **Incident history**: Each chaos incident now shows duration, impact percentage, and source metadata instead of just a label.

---

## [1.5.0] - 2026-04-21

### Deterministic Chaos & Lifecycle State Machine

> The original Chaos Playground triggered visual changes but didn't model what a real system in failure actually does: degrade progressively, attempt recovery, stabilize, then potentially fail again. Adding hysteresis thresholds and a real state machine made the simulation behave like a system under real load rather than a UI toggle.

#### Added
- **Stateful decision engine** (`useDecisionEngine.ts`): Manages `NORMAL → DEGRADED → RECOVERING → STABLE` lifecycle transitions with hysteresis thresholds. A state transition requires sustained threshold violation, not a single spike — this prevents flapping.
- **Deterministic chaos presets** (`off`, `mild`, `stress`, `failure`): Injected via `X-Chaos-Preset` header. Each preset affects retry posture, cache TTL expectations, and lifecycle presentation — not just failure visuals.
- **Architecture trade-offs section**: Documents real engineering compromises with operational impact: Latency vs. Consistency (stub-revalidate for UI smoothness, real-time polling for accuracy), Sync vs. Async (chaos actions synchronous for control panel feedback, async for observability pipeline), Structured vs. Text logging (structured for tooling, cost is human readability in raw form).
- **Post-mortem Case Study #0042** (Redis Connection Leak): Featured archived incident — unhandled exception in the ingestion worker caused Redis connection pool exhaustion, 12.4% error rate, 14-minute MTTR. Included because it shows a realistic failure mode: the hysteresis engine prevented oscillation while the root cause was isolated.

#### Fixed
- **Defensive field access in `api.py` and `chaos.py`**: `KeyError` exceptions during rapid state transitions were causing 500s. Added `.get()` with fallbacks throughout the chaos state handlers.

---

## [1.4.2] - 2026-04-20

### Observability Infrastructure

> `/metrics` showed aggregate error rates. Sentry showed stack traces. But there was no way to correlate a specific user action in the frontend with the backend request that served it. Adding `trace_id` propagation across the full stack closed that gap.

#### Added
- **`MetricsSparkline` component**: Linear sparkline with threshold lines and vertical incident markers. Renders real P95 telemetry with visual distinction between normal, degraded, and recovering states.
- **Extended `useLiveMetrics`**: Keeps timestamped sample history, baseline P95, recent traces, latest event, circuit-breaker state, and timeout state — not just the latest value.
- **`trace_id` propagation**: `ChaosPlayground` now emits `trace_id` per action. `TraceViewer` and `LogStream` display both `request_id` (backend-generated) and `trace_id` (frontend-initiated) for end-to-end correlation.
- **Enriched contact response**: `RespostaContato` now returns `queue_status`, `delivery_mode`, and `downstream` — the frontend displays the full request lifecycle, not just "sent".

#### Fixed
- **LogStream auto-scroll**: Was calling `window.scrollTo` globally, scrolling the entire page instead of staying inside the terminal container. Scoped to the terminal's `scrollTop`.
- **Privacy**: Contact details in the footer obfuscated (`ar***@gmail.com`, `(+x) x ****-3364`).

---

## [1.4.1] - 2026-04-19

### Cold Start Resolution & Chaos Engineering Foundation

> See INC-002 for the full cold start incident. This release resolves it and adds the honest Chaos Playground — "honest" because it labels simulated failures explicitly rather than implying they reflect real backend state.

#### Added
- **Honest Chaos Playground**: Interactive failure simulation with explicit labeling that chaos actions are synthetic. Each action affects the metrics visible above — the connection between action and consequence is immediate.
- **`TraceConsole` UI**: Allows repeated payload testing without reloading. Contact form doubles as a live API inspector showing request lifecycle.

#### Performance
- **Cold start fix**: Removed `alembic upgrade head` from container boot. Updated keep-alive cron targets to `/health` (fast, no DB) instead of data endpoints (slow, requires PostgreSQL). See INC-002 and ADR-03.

---

## [1.4.0] - 2026-04-15 · Production Release

> First version deployed to `argenisbackend.com`. The release exposed INC-004 (CSP blocking API calls) immediately after deploy — it was resolved within the same day.

#### Added
- **Custom domain**: `argenisbackend.com` configured with Vercel (frontend) and Koyeb (backend at `api.argenisbackend.com`).
- **Resend for email delivery**: Replaced Formspree. Resend provides delivery status, webhook support, and structured logging — Formspree was a black box.
- **Factual metrics dashboard**: Removed decorative charts. All displayed values are either real API data or explicitly labeled as synthetic.

---

## [1.3.1] - 2026-04-11

### Security Hardening

#### Added
- **`TRUSTED_PROXY_DEPTH` validation**: Prevents IP spoofing via `X-Forwarded-For` header manipulation. Without this, a client could set their own `X-Forwarded-For` to bypass IP-based rate limiting — the backend would use the attacker-provided IP instead of the real one.
- **PII masking in logs**: Sender email addresses in structured logs are automatically masked. Required for GDPR/LGPD compliance — the logs are exported to external services (OpenTelemetry, Sentry) and should not contain raw contact information.

#### Fixed
- **Multi-worker idempotency warning**: Added explicit warning when the in-memory idempotency store is running without Redis in a multi-worker environment. Previously, this was a silent misconfiguration — two workers with independent in-memory stores meant duplicate messages could pass idempotency checks.

---

## [1.3.0] - 2026-04-04

### Persistent State — Redis + PostgreSQL

> See INC-001 for the full incident that forced this release. The short version: in-memory rate limiting on an ephemeral container is not rate limiting — it's a counter that resets on every restart.

#### Added
- **Redis-backed rate limiting** (Upstash): Rate limit counters now survive container restarts and are consistent across replicas. The previous in-memory implementation was silently non-functional in production.
- **PostgreSQL persistence** (Supabase via `asyncpg`): Contact submissions deduplicated by hash. State survives the container lifecycle entirely.
- **Defense-in-depth middleware**: HSTS, X-Content-Type-Options, X-Frame-Options on every backend response. See ADR-10.
- **GZip compression**: Payloads >1KB compressed. Measurable improvement on low-bandwidth connections for the full portfolio data response.

---

## [1.2.0] - 2026-04-01

### Observability Stack

#### Added
- **Prometheus `/metrics`**: Request rates, latency histograms, error rates. Basic Auth required in production — see ADR-04.
- **Sentry** on both FastAPI and React: Stack traces + breadcrumbs for failures that metrics can't diagnose. See ADR-09.
- **OpenTelemetry tracing**: Distributed trace context for cross-service correlation.

---

## [1.1.0] - 2026-03-22

### CORS — Dynamic Preview Support

> Vercel preview URLs are generated per PR and can't be hardcoded. The first PR after deployment was blocked by CORS. Rather than maintaining a growing allow-list, a regex covers all legitimate preview domains.

#### Added
- **Regex-based CORS** (`^https://argenisbackend\.com|https://portfolio.*-argenis1412s-projects\.vercel\.app$`): All Vercel previews allowed automatically. See ADR-06.
- **CORS preflight tests**: Automated `OPTIONS` request tests ensure the policy is correct before any deployment.

---

## [1.0.0] - 2025-11-10 · Initial Release

**Backend**
- FastAPI with Clean Architecture (Controllers → Use Cases → Entities → Adapters)
- API versioning at `/api/v1/`
- 6 endpoints: `about`, `projects`, `stack`, `experiences`, `contact`, `health`
- Pydantic V2 validation, custom exception system, global error handlers
- Observability middleware: request ID injection, structured logging, performance tracking
- JSON persistence with adapter interface ready for PostgreSQL migration
- 80% minimum test coverage enforced in CI (17 tests, pytest + asyncio)

**DevOps**
- Multi-stage Dockerfile, Docker Compose, GitHub Actions CI (backend + frontend)
- `.env.example` with documented variables

**Documentation**
- `ARCHITECTURE.md` (this file's predecessor), `CHANGELOG.md`, `README.md`, deployment guide, testing guide, API reference

---

## Versioning

- **MAJOR** (1.x.x): Breaking API changes
- **MINOR** (x.1.x): New features, backwards compatible
- **PATCH** (x.x.1): Bug fixes

---

[1.6.0]: https://github.com/Argenis1412/portfolio/releases/tag/v1.6.0
[1.5.1]: https://github.com/Argenis1412/portfolio/releases/tag/v1.5.1
[1.5.0]: https://github.com/Argenis1412/portfolio/releases/tag/v1.5.0
[1.4.2]: https://github.com/Argenis1412/portfolio/releases/tag/v1.4.2
[1.4.1]: https://github.com/Argenis1412/portfolio/releases/tag/v1.4.1
[1.4.0]: https://github.com/Argenis1412/portfolio/releases/tag/v1.4.0
[1.3.1]: https://github.com/Argenis1412/portfolio/releases/tag/v1.3.1
[1.3.0]: https://github.com/Argenis1412/portfolio/releases/tag/v1.3.0
[1.2.0]: https://github.com/Argenis1412/portfolio/releases/tag/v1.2.0
[1.1.0]: https://github.com/Argenis1412/portfolio/releases/tag/v1.1.0
[1.0.0]: https://github.com/Argenis1412/portfolio/releases/tag/v1.0.0