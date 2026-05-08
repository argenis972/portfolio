# Explicit Failure Model & Contingency Policies

> This document is grounded in real production incidents (INC-001 through INC-009).
> Each failure mode documents what actually happened, how it was detected, the accepted degradation behavior, and the governing ADR.
> Source: CHANGELOG.md (Production Incidents section).

---

## 1. Rate Limiter Storage Failure (In-Memory State Loss)

### Incident: INC-001 — Rate Limiter Silently Disabled in Production
- **Period:** v1.2.0 → v1.3.0 (~2 weeks)
- **Affected:** `POST /api/v1/contact` — anti-spam protection

### Actual Failure
In-memory rate limiting counters (via `slowapi`) reset to zero on every Koyeb container restart. The free tier restarts containers on inactivity, redeploys, and occasionally without visible reason. Anti-spam protection was effectively non-functional — a user could bypass the limit by waiting for a natural container cycle (every few hours).

### Detection
**Manual discovery.** Not caught by an alert. Discovered during a routine test of the contact endpoint the day after a redeploy, when the rate limit counter had clearly reset.

### Accepted Degradation Behavior
- **Fail-open pattern:** If Redis (Upstash) is unavailable, the rate limiter fails open — requests pass through unthrottled.
- **Rationale:** Failing closed would block legitimate contact attempts during an infrastructure outage. An open rate limiter is a spam risk; a closed one is a service outage.

### Governing ADR
- **ADR-11:** External Storage for Distributed State — migrated rate limiting from local memory to Redis (Upstash) for persistence across container restarts.

### Accepted Consequence
Redis is now in the critical path for `/contact`. If Upstash is unavailable, anti-spam protection is non-functional until Redis recovers.

---

## 2. Database Cold Start Latency (Static Data Path)

### Incident: INC-002 — Cold Start Latency Making Keep-Alive Useless
- **Period:** v1.2.0 → v1.4.1
- **Affected:** First portfolio data request after Koyeb container sleep

### Actual Failure
Keep-alive cron pinged `/health` every 14 minutes to prevent container sleep. The container stayed warm, but P95 on the first portfolio data request was still 280–400ms. The bottleneck was the PostgreSQL (Supabase) connection being re-established for every data read, regardless of whether the container was warm.

### Detection
**Keep-alive metrics showed healthy container, but user-facing latency metrics revealed the gap.** The keep-alive was hitting a fast endpoint while the actual slow path (PostgreSQL connection) went unmonitored by the cron.

### Accepted Degradation Behavior
- **JSONRepository fail-silent:** Static portfolio data is served from memory-cached JSON files loaded at startup. No database round-trip for reads.
- **Rationale:** Static data does not require real-time consistency. A redeploy is an acceptable update mechanism for portfolio content.

### Governing ADR
- **ADR-05:** JSON-First Read Path — prioritizing `JSONRepository` for all portfolio-related reads in production. PostgreSQL reserved for transactional data only.

### Accepted Consequence
Updating portfolio content now requires a container redeploy, not a database update. This is intentional — the trade-off favors latency over content agility.

---

## 3. Chaos Playground Crash on Database Unavailability

### Incident: INC-003 — Chaos Playground Crashing on Database Unavailability
- **Period:** v1.4.x
- **Affected:** Entire Chaos Playground UI

### Actual Failure
During a brief Supabase connectivity issue, the database write in the chaos action handler raised an unhandled exception that propagated up through the entire handler. The playground crashed completely — not because the simulation failed, but because a secondary operation (recording the incident to PostgreSQL) failed.

### Detection
**Manual testing** during a Supabase connectivity issue. No automated alert caught this — the failure was observed directly in the playground UI.

### Accepted Degradation Behavior
- **Fail-silent pattern:** All chaos persistence calls are wrapped in try/except. Database write failures are logged but do not interrupt the simulation. The playground completes its primary job (running the simulation) even when its secondary job (recording to DB) fails.
- **Rationale:** This is a demo tool, not a production incident recorder. The simulation is the primary function; persistence is secondary.

### Governing ADR
- **ADR-15.1:** Resilient Chaos Persistence — chaos actions must not depend on database availability to complete their primary task.

### Accepted Consequence
Incidents that occur during a database outage are silently lost from the history panel. Acceptable for a demo tool.

---

## 4. CSP Blocking Frontend-Backend Communication

### Incident: INC-004 — CSP Blocking Frontend ↔ Backend Communication in Production
- **Period:** v1.3.x → v1.4.0
- **Affected:** All API calls from the deployed frontend

### Actual Failure
After configuring the custom domain `argenisbackend.com`, the browser started blocking all API calls. The Content Security Policy in `vercel.json` did not include `api.argenisbackend.com` as an allowed `connect-src`. Development used `localhost`; staging used Vercel preview URLs with different CSP. The production CSP was only applied after the custom domain was configured — the first time anyone tested the full production path.

### Detection
**Browser console CSP violations** in production. Discovered immediately after the v1.4.0 deploy to `argenisbackend.com`. Not caught by automated tests because the CSP config was environment-specific.

### Accepted Degradation Behavior
- **Complete communication failure:** When CSP blocks `connect-src`, no API calls succeed. There is no graceful degradation — the frontend cannot reach the backend at all.
- **Prevention mechanism:** CSP and CORS must be updated together. Separate changes to either without the other will cause this failure to recur.

### Governing ADR
- **ADR-15.3:** Security Header & CORS Synchronization — single source of truth for allowed origins, CSP whitelists `api.argenisbackend.com`, CORS regex covers the corresponding origin.

### Accepted Consequence
CSP/CORS synchronization is a manual coordination requirement. Adding a new domain requires updating both `vercel.json` and `settings.py` in the same release.

---

## 5. Docker Build Context Mismatch (Deployment Blocker)

### Incident: INC-005 — Monorepo Build Context Mismatch
- **Period:** v1.6.0
- **Affected:** CI/CD Pipeline & Deployment (Koyeb + GitHub Actions)

### Actual Failure
Deployments failed on Koyeb with `file not found` errors for `requirements.txt` and `app/`. Fixing it for Koyeb (building from root) broke GitHub Actions, which was configured to build from inside `/backend`. Forcing the "Work Directory" to `/backend` in Koyeb made things worse by creating an absolute discrepancy between the Dockerfile context and the runner's actual filesystem.

### Detection
**CI/CD pipeline failure.** GitHub Actions reported build errors. Koyeb deployment also failed. Not a runtime issue — this was a build-time failure.

### Accepted Degradation Behavior
- **Deployment blocked, previous version remains active.** When the build fails, the existing deployment stays live. No user-facing impact, but new code cannot ship until the build context is consistent.
- **Rationale:** Build failures are preferable to deploying a broken image.

### Governing ADR
- **ADR-15.2:** Monorepo Build Standardization — unified build context from the repository root for all environments (Koyeb, GitHub Actions, Local).

### Accepted Consequence
Local builds now also require being run from the repository root. The `Dockerfile` uses prefixed paths (`COPY backend/requirements.txt`).

---

## 6. Spam Filter False Positive on Mixed-Protocol Links

### Incident: INC-006 — Spam Filter Accuracy
- **Period:** v1.7.x → v1.8.0
- **Affected:** `POST /api/v1/contact` — spam scoring (link count)

### Actual Failure
The regex `https?://[^\s]+|www\.[^\s]+` treated URLs delimited by commas as a single token (e.g., `https://a.com,https://b.com` → 1 link). The link count was underestimated, which reduced the spam score below the threshold of 3 links.

### Detection
**Static analysis bot** during PR review. Discovered as a potential vulnerability that would allow link-heavy spam to bypass the multi-link penalty.

### Accepted Degradation Behavior
- **False negatives in spam scoring:** Messages with multiple links in non-standard formats passed as single-link (score +15 vs +45 expected).
- **Rationale:** Prioritizing deliverability over aggressive filtering. A false negative (spam gets through) is preferable to a false positive (legitimate message dropped).

### Governing ADR
- **ADR-18:** (Or refer to CHANGELOG for Anti-spam Accuracy Improvement). Unified URL extraction excluding delimiters `, ; ( ) [ ]` from the match. Normalization strips trailing prose punctuation.

### Accepted Consequence
Spam filter must be continuously monitored and regexes adjusted. The system is designed to allow some spam to prevent blocking valid inquiries.

---

## 7. Koyeb Terraform Provider Schema Incompatibility

### Incident: INC-007 — Infrastructure Provisioning Blocked by Provider Limitation
- **Period:** v1.7.0 → v1.8.1
- **Affected:** Infrastructure Provisioning CI/CD (Terraform)

### Actual Failure
The migration to Terraform was blocked by a `400 Bad Request` from the Koyeb API: `env type is required`. The official Terraform provider (v0.1.11) lacked the schema fields to send this mandatory metadata for literal environment variables, making the standard `env` block unusable.

### Detection
**CI/CD pipeline failure.** Terraform apply failed with an API error during the first automated provisioning attempt.

### Accepted Degradation Behavior
- **Deployment blocked:** New infrastructure changes cannot be applied until the configuration is refactored to bypass the limitation.
- **Architectural pivot:** Pivoted to "Secret-First Orchestration". All configuration is now vaulted as Koyeb Secrets, which have an implicit type in the API, bypassing the provider's literal `env` schema bug.

### Governing ADR
- **ADR-18:** Infrastructure as Code (IaC) — specifically the "Secret-First" pivot documented in the changelog.

### Accepted Consequence
All configuration variables (including non-sensitive ones) are now managed as secrets. This increases the manual effort to rotate or view variables in the UI but improves the security posture.

---

## 8. Destructive IaC Migration (Free Tier Constraints)

### Incident: INC-008 — Cold Migration Downtime
- **Period:** v1.7.1 → v1.8.1 (Migration Window)
- **Affected:** Global API Availability (`api.argenisbackend.com`)

### Actual Failure
Koyeb Free Tier prevents multiple services from claiming the same custom domain. To move from manual management to Terraform ownership, the manual service had to be deleted before the Terraform one could be created. This resulted in a 14-hour downtime window.

### Detection
**Planned maintenance.** Discovered during the trial import of the custom domain into Terraform state.

### Accepted Degradation Behavior
- **Intentional downtime:** A "Cold Migration" strategy was chosen over zero-downtime to ensure 100% operational consistency and eliminate all legacy "shadow" configuration.
- **Rationale:** For a portfolio/SRE demo project, full reproducibility and IaC integrity are higher priorities than 99.9% uptime during a one-time migration.

### Governing ADR
- **ADR-18:** Infrastructure as Code (IaC) — transition from manual to automated management.

### Accepted Consequence
Downtime is accepted for destructive reconciliation when provider ownership constraints prevent seamless imports.

---

## 9. Terraform Secret Identity Collision (Rename Race Condition)

### Incident: INC-009 — Secret Identity Collision
- **Period:** v1.8.1 → v1.8.2
- **Affected:** Infrastructure Provisioning CI/CD (Terraform)

### Actual Failure
Renaming Terraform resource keys in a `for_each` map (e.g., `ENVIRONMENT` → `AMBIENTE`) triggered a `destroy + create` cycle. Because both keys mapped to the same physical Koyeb secret name, the "create" step failed with a `400 Bad Request: already exists` error. Terraform does not natively recognize key changes as renames without explicit instruction.

### Detection
**CI/CD pipeline failure.** Terraform apply failed during the "English-First" standardization phase.

### Accepted Degradation Behavior
- **Deployment blocked:** Infrastructure cannot be updated until the state is manually reconciled or `moved` blocks are added.
- **Remediation:** Implementation of `moved` blocks to convert destructive cycles into state-only renames.

### Governing ADR
- **ADR-18:** Infrastructure as Code (IaC) — specifically the "Zero to Destroy" principle.

### Accepted Consequence
Renaming internal Terraform keys now requires mandatory `moved` blocks to maintain state continuity.

---

## Failure Mode Summary

| Incident | Component | Detection | Degradation | ADR | Status |
|:---|:---|:---|:---|:---|:---|
| INC-001 | Rate Limiter (Redis) | Manual | Fail-open (requests pass unthrottled) | ADR-11 | Resolved v1.3.0 |
| INC-002 | Static Data Path (PostgreSQL) | Metrics gap | Fail-silent (JSONRepository, no DB) | ADR-05 | Resolved v1.4.1 |
| INC-003 | Chaos Persistence (PostgreSQL) | Manual | Fail-silent (simulation continues, logs lost) | ADR-15.1 | Resolved v1.4.x |
| INC-004 | CSP/CORS (Browser) | Browser console | Complete block (no graceful degradation) | ADR-15.3 | Resolved v1.4.0 |
| INC-005 | Docker Build Context | CI/CD failure | Deployment blocked, previous version stays | ADR-15.2 | Resolved v1.6.0 |
| INC-006 | Spam Filter (Contact) | Static analysis | False negatives (spam passes as single-link) | CHANGELOG | Resolved v1.8.0 |
| INC-007 | Terraform Provider | CI/CD failure | Deployment blocked (Architectural pivot to Secrets) | ADR-18 | Resolved v1.8.1 |
| INC-008 | IaC Migration | Manual | Intentional downtime (Cold Migration) | ADR-18 | Resolved v1.8.1 |
| INC-009 | Terraform Resource | CI/CD | Deployment blocked (Identity Collision) | ADR-18 | Resolved v1.8.2 |

---

## Degradation Telemetry

When any component enters a degraded state, the API response includes a formalized metadata block:

```json
{
  "status": "success",
  "data": { ... },
  "system_telemetry": {
    "status": "degraded",
    "degraded_components": ["postgresql"],
    "active_circuit_breakers": 1
  }
}
```

This structure is implemented per ADR-13 (Frontend Observability Enhancements) and displayed in the `LiveMetricsBento` component with failure-model panel and telemetry timeline.

---

## References

- **Incident Source:** CHANGELOG.md (Production Incidents section)
- **Architecture Decisions:** ARCHITECTURE.md (ADR-05, ADR-11, ADR-13, ADR-15)
- **SLO Targets:** SLO_DEFINITIONS.md
- **Engineering Standards:** ENGINEERING_PLAYBOOK.md
