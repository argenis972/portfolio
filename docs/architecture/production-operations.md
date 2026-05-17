# Production Operations Runbook

This document defines the minimum operational requirements for a secure and scalable
production deployment, and provides step-by-step runbooks for the most common
operational tasks.

---

## 1. Required Production Variables

The backend requires the following variables when `AMBIENTE=producao`:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | ✅ | Must use `postgresql+asyncpg://` |
| `REDIS_URL` | ✅ | Required for rate limiting, idempotency, and dedup |
| `METRICS_BASIC_AUTH_USERNAME` | ✅ | Basic auth for `/metrics` |
| `METRICS_BASIC_AUTH_PASSWORD` | ✅ | Basic auth for `/metrics` |
| `RESEND_API_KEY` | ⚠️ | Required for contact delivery |
| `REDIS_SOCKET_TIMEOUT_SECONDS` | Optional | Default: 5s |
| `REDIS_CONNECT_TIMEOUT_SECONDS` | Optional | Default: 5s |
| `DB_CONNECT_TIMEOUT_SECONDS` | Optional | Default: 5s |
| `DB_COMMAND_TIMEOUT_SECONDS` | Optional | Default: 10s |
| `SENTRY_DSN` | Optional | Enables Sentry error tracking |
| `OTLP_ENDPOINT` | Optional | Enables OTLP trace export |

---

## 2. Deploy Runbook

**Trigger:** after merging a PR to `main`.

```
Step 1 — Verify CI
  - Confirm all GitHub Actions jobs (test, lint, build) are green on main.
  - Do not deploy from a branch or from a failing pipeline.

Step 2 — Push to Koyeb
  - Koyeb is configured for auto-deploy on push to main.
  - If auto-deploy is disabled, trigger manually:
    koyeb service redeploy <service-name>

Step 3 — Monitor startup
  - Watch Koyeb deployment logs for errors.
  - Startup should complete in < 30s.
  - Look for: "Application startup complete."

Step 4 — Validate readiness
  - GET /live    → must return HTTP 200
  - GET /health  → must return {"status": "ok"} with all deps healthy

Step 5 — Smoke test
  - Submit a test contact form and verify it is received.
  - Check /metrics is protected (must require Basic Auth in production).
```

---

## 3. Rollback Runbook

**Trigger:** after a deploy that causes regressions (5xx spike, startup failure, broken contact form).

```
Step 1 — Identify the last good commit
  git log --oneline -10          # find the last known-good SHA

Step 2 — Rollback in Koyeb (preferred)
  - Go to Koyeb dashboard → Service → Deployments
  - Click the previous green deployment → "Redeploy"
  - This re-deploys the previous Docker image without a code push.

Step 3 — Alternatively: revert and push
  git revert HEAD                # or git revert <bad-sha>
  git push origin main
  # Koyeb auto-deploys the reverted commit.

Step 4 — Validate recovery
  - GET /live    → HTTP 200
  - GET /health  → {"status": "ok"}
  - Verify 5xx rate returns to baseline in Prometheus/Sentry.

Step 5 — Post-rollback
  - Open a GitHub Issue with the revert reason.
  - Do NOT close the incident until root cause is identified.
```

---

## 4. Secret Rotation Runbook

Rotate secrets **immediately** when a value is exposed in logs, screenshots, chat
history, or browser history.

```
Step 1 — Rotate at the provider
  - Supabase: Settings → Database → Reset password
  - Redis (Upstash): Console → Reset token
  - Metrics auth: generate new random credentials locally
  - Resend: Dashboard → Revoke API Key if compromised

Step 2 — Update Koyeb environment variables
  - Koyeb dashboard → Service → Environment
  - Update the affected variable.
  - Do NOT commit secrets to the repository.

Step 3 — Redeploy
  koyeb service redeploy <service-name>

Step 4 — Validate
  - GET /live    → HTTP 200
  - GET /health  → {"status": "ok", ...} with database/redis showing "ok"
  - Try the contact form end-to-end.
  - Verify old credentials no longer work.

Step 5 — Close incident
  - Only after confirming old credentials are inactive.
  - Add a note to the incident report.
```

Priority order for rotation:

1. Supabase database password
2. Redis token / password
3. Metrics Basic Auth credentials
4. Resend API Key (if the form received spam or was leaked)
5. Sentry DSN (only if project scope changes)

---

## 5. Incident Response

### Triage Checklist

```
1. Check /live          → if DOWN: Koyeb instance is crashed. Rollback immediately.
2. Check /health        → if degraded: identify which dependency (db/redis) is failing.
3. Check Sentry        → look for new exceptions or error rate spikes.
4. Check Prometheus    → check 5xx rate, P95 latency, contact delivery failures.
5. Check Koyeb logs    → look for OOM kills, timeout errors, startup failures.
```

### Escalation

| Severity | Condition | Action |
|---|---|---|
| P1 | /live returns non-200 | Rollback immediately |
| P2 | /health shows DB or Redis error | Investigate provider status, rotate if needed |
| P3 | 5xx rate > 2% for 5 min | Check Sentry for root cause |
| P4 | Contact form not delivering | Check Resend status / credentials |

### Post-Mortem Template

```markdown
## Incident: <title>

**Date:** YYYY-MM-DD
**Duration:** N minutes
**Severity:** P1 / P2 / P3 / P4

### What happened
<Brief factual description>

### Timeline
- HH:MM: First alert / detection
- HH:MM: Diagnosis
- HH:MM: Mitigation applied
- HH:MM: Service recovered

### Root cause
<Technical root cause>

### Impact
<Who was affected and how>

### Action items
- [ ] Item 1
- [ ] Item 2
```

---

## 6. Metrics Access Policy

`/metrics` must not be public in production.

| Environment | Access |
|---|---|
| local / test | Open (no auth) |
| production | HTTP Basic Auth required |

---

## 7. Minimum Alert Thresholds

Recommended thresholds:

1. `5xx rate > 2% for 5 minutes`
2. `P95 latency > 1.5s for 10 minutes`
3. `contact delivery failures > 5 in 10 minutes`
4. `database connection errors > 3 in 5 minutes`
5. `redis connection errors > 3 in 5 minutes`

Suggested sinks:
- Sentry for exceptions and contact delivery failures
- Prometheus / Grafana for latency, traffic, and infrastructure thresholds

---

## 8. Readiness and Liveness Probes

| Endpoint | Purpose | Use |
|---|---|---|
| `/live` | Process liveness only (no deps) | Koyeb liveness probe |
| `/health` | Readiness with real dependency checks | Koyeb readiness probe / diagnostics |

Use `/live` for lightweight keep-alive probes.
Use `/health` in production diagnostics and incident triage.

> **Note:** `/saude` and `/salud` remain active as deprecated aliases (since v1.9.2).
> Canonical endpoint is `/health`. Aliases will be removed in v1.9.3.

---

## 9. Tracing (Jaeger/OTLP) Notes

- Sentry tracing works automatically via `SENTRY_DSN` (do not also set `OTLP_ENDPOINT`
  to a Sentry URL — they are separate pipelines).
- If `OTLP_ENDPOINT` is empty in production, spans are not exported (Console exporter
  is disabled to avoid noise).
- For Jaeger/Tempo, configure `OTLP_ENDPOINT` with an accessible HTTP endpoint
  (e.g. `https://<host>:4318`). Localhost Jaeger is not reachable from Koyeb.
