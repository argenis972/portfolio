# 📜 Engineering Playbook

> Standards are only useful when you understand why they exist.
> Each rule here has a reason — usually a failure that made it necessary.

---

## 1. Commit Protocol

**Format**: `type(scope): description` — [Conventional Commits](https://www.conventionalcommits.org/)

| Type | When to use |
|:---|:---|
| `feat` | New capability visible to users or API consumers |
| `fix` | Corrects broken behavior |
| `perf` | Measurable performance improvement — document the before/after |
| `refactor` | Internal restructuring with no behavior change |
| `test` | Tests only — no production code |
| `docs` | Documentation only |
| `ci` | CI/CD pipeline changes |
| `chore` | Dependency bumps, tooling, build config |

**Atomic commits**: One logical change per commit. A feature and its refactor are separate commits — reviewers shouldn't have to untangle them.

**`ci:` commits are prioritized above all other work.** A broken pipeline blocks everyone. Fix it first.

---

## 2. Branch Naming

Pattern: `type/short-description` — lowercase, hyphens only, max ~4 words after the prefix.

```
feat/redis-rate-limiting
fix/cors-csp-domain-sync
refactor/api-layer-modular
docs/add-adr-synthetic-telemetry
chore/upgrade-pydantic-v2
```

No underscores. No uppercase. No ticket numbers unless the team uses an issue tracker actively.

---

## 3. CI/CD — Green Pipeline Before Merge

No merge to `main` without passing:

1. **`lint`** — `ruff` + `mypy`. Style is not negotiable and is not a human reviewer's job.
2. **`test`** — Full suite, coverage threshold enforced. A threshold that's never failed is too low.
3. **`build`** — Docker build succeeds. This proves the artifact is deployable, not just that the code compiles.

**Why this matters in this project**: The `/saude` → `/health` rename in v1.4.1 required updating the Dockerfile `HEALTHCHECK`, the keep-alive cron, GitHub Actions healthcheck, and three test fixtures. Missing any one of them caused a silent CI pass but a broken production deploy. The build step catches this class of failure.

---

## 4. Architecture

**Clean Architecture layers**: `Controllers → Use Cases → Entities → Adapters`

The rule that matters most: **business logic must not import from infrastructure**. FastAPI, SQLAlchemy, Redis — none of these should appear in the domain or use case layers. If they do, the architecture has collapsed.

**The concrete test**: Can you swap `JSONRepository` for `PostgreSQLRepository` without touching a single controller? In this project, yes — that swap happened in v1.4.1 with zero controller changes. That's the proof the boundary works.

**Framework independence in the domain layer**: If you need to mock a framework to test business logic, the dependency is in the wrong place.

---

## 5. Definition of Done

A task is **not done** until:

- [ ] Passes `ruff`, `mypy`, and `pytest` locally
- [ ] New logic has unit tests with a named failure scenario (`test_<unit>_<scenario>_<expected>`)
- [ ] If system behavior changed: `README.md`, `ARCHITECTURE.md`, or `CHANGELOG.md` updated
- [ ] No placeholder values, no TODO comments in committed code
- [ ] Environment variables documented in `.env.example`

**On documentation**: Updating `ARCHITECTURE.md` is not optional when an ADR-worthy decision is made. The document exists precisely because undocumented decisions become mysteries six months later.

---

## 6. Observability & Security

**Structured logging**: Use `structlog` (or equivalent). Log entries are machine-readable first. Fields that matter on every request: `request_id`, `trace_id`, `status_code`, `latency_ms`, `path`.

**Public endpoints**: Rate limiting + idempotency key + honeypot validation as defaults. Not optional additions.

**Silent drops for spam/abuse**: Rejected requests return `200 OK` with a neutral response — never `429` or `403` that confirms the filter was triggered. Feedback to attackers is information.

**PII in logs**: Mask before export. Sentry and OpenTelemetry exporters receive log data. Contact form fields, email addresses, and user-identifiable data must be scrubbed before leaving the process. This is not optional if the project handles any contact or personal data.

**Metrics endpoint**: `/metrics` requires Basic Auth in production. A public metrics endpoint exposes internal system behavior to anyone who finds it. Intentionally accessible ≠ publicly indexed.

---

## 7. API Design

**Versioning from day one**: All routes at `/api/v1/...`. Breaking changes get a new version prefix — never silently change an existing response shape.

**Consistent error schema**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests from this origin.",
    "trace_id": "req-abc123"
  }
}
```
Never return raw strings. Never return HTML error pages from an API endpoint. Both have happened in this codebase — both caused confusing frontend behavior.

**Idempotency keys on mutating endpoints**: `POST /contact` accepts `Idempotency-Key`. Resubmitting the same key returns the original response without side effects. Without this, network retries create duplicate submissions.

**No unbounded lists**: Default `limit=20`, max `limit=100`. An endpoint that returns everything is a denial-of-service vector and a performance cliff waiting to be discovered.

---

## 8. Dependency & Environment Hygiene

**Exact version pins in production**: `requirements.txt` uses `==`, not `>=`. A range that installs successfully today may fail after an upstream release. Found out the hard way with a transitive Pydantic dependency in early v1.x.

**Secrets never in code**: All credentials in `.env` (local) or the cloud provider's secret manager. `.env.example` documents the variables without values. If a secret is committed accidentally — rotate it immediately, don't just delete it from git history.

**New dependency checklist before adding**:
1. Can the standard library or an existing dependency solve this?
2. What's the maintenance status of the package?
3. Does it add to the Docker image size meaningfully?
4. Does it require a new environment variable in production?

---

## 9. Data Integrity & Migrations

**Migrations are never destructive by default**. The pattern for removing a column:
1. Add new column, deploy.
2. Migrate data to new column, deploy.
3. Remove old column in a later release cycle.

Dropping a column directly in production has no rollback path if the deploy fails halfway.

**Explicit transactions**: Any operation touching multiple tables lives in a transaction. If the ORM handles it implicitly — document it so the next person doesn't assume it's absent.

**Soft deletes for critical entities**: `deleted_at TIMESTAMP NULL`. Never physically delete users, orders, or contact records. Audit trails matter.

---

## 10. Testing Strategy

**70/20/10**: Unit / Integration / E2E. Never invert the pyramid — integration tests that take 30 seconds each don't get run.

**Test naming**: `test_<unit>_<scenario>_<expected_result>`
```python
test_contact_with_duplicate_idempotency_key_returns_original_response
test_rate_limiter_after_container_restart_preserves_counter  # ← the test that caught INC-001
test_chaos_persistence_failure_does_not_crash_simulation     # ← the test that caught INC-003
```

**No mocks in the domain layer**: If a use case requires a mock to test, the use case has an infrastructure dependency it shouldn't have.

**Deterministic fixtures**: Seeds and factories. Never use production data in tests. Never generate random data without a fixed seed.

---

## 11. Performance

**Document the SLO before optimizing**: Write down the target before writing the code. Current targets for this project:
- Static portfolio data (`/about`, `/projects`, `/stack`): P95 < 50ms
- Contact endpoint (`/contact`): P95 < 200ms (includes Redis round-trip)
- Health check (`/health`): P99 < 100ms *(Recalibrated from 20ms to reflect Koyeb Free Tier cold-start network constraints; P95 Cold: ~3.5s, P95 Warm: ~1.3s)*

**N+1 is a bug, not a todo**: A query inside a loop is a defect. Detect with `EXPLAIN ANALYZE` before it reaches production.

**Document cache strategy explicitly**: TTL, invalidation trigger, and behavior on cache miss. The `JSONRepository` has an implicit cache (files loaded at startup, never invalidated until restart). That's a valid strategy — but it's documented so the next person knows it's intentional.

---

## 12. Code Review

**Author prepares the PR**: Description includes context, what changed, why, and what to look for. A reviewer who has to ask "what does this do?" is reading an incomplete PR.

**Reviewer approves logic, not style**: `ruff` handles style. Human comments are for correctness, security, and design decisions.

**Two-pass review**:
1. First pass: read the full diff to understand the intent.
2. Second pass: review line by line for correctness.

Reviewing line by line without understanding the intent produces comments about variable names and misses architectural problems.

---

## 13. Incident Protocol

**Every significant production incident produces a post-mortem.** Format (same as CHANGELOG `🔥 Production Incidents` section):

```
### INC-XXX · Title
Period: which versions were affected
Affected: which endpoints/components

What happened: observable symptoms
How it was discovered: not how you wish you'd found it — how you actually found it
What was tried first (if it didn't work): first hypothesis and why it failed
Root cause: actual cause
Resolution: what fixed it
Accepted side effects: what the fix broke or constrained
```

**Blameless**: The document names systems and decisions, not people.

**Reproducibility before fixing**: Write the test that reproduces the bug. The fix makes the test pass. This applies to all three fixed in this project: INC-001 (rate limiter), INC-003 (chaos crash), INC-004 (CSP block).

---

## 14. Documentation

**Language**: All `.md` files, commit messages, PR descriptions, and branch names are in English. Internal identifiers (routes, field names, directory names) are in English. User-facing content supports EN/ES/PT via i18n — this is separate from codebase language. **Incident post-mortems** specifically stay in English across all locales (en/es/pt): they are professional engineering artifacts where translation adds maintenance overhead without meaningful benefit.

**ADRs**: Any non-obvious architectural decision goes in `ARCHITECTURE.md` with context, decision, and consequences. "Non-obvious" means: if you'd have to explain it in a code review, it needs an ADR.

**CHANGELOG**: Documents what changed and why it mattered. Not a git log. Not a feature list. See the `🔥 Production Incidents` section for the standard incident format.

**Docstrings on public interfaces**: Every public function and class has a docstring. Internal helpers can omit if self-explanatory. "Self-explanatory" means a new contributor understands it without asking.

---

## 15. AI-Assisted Development

- Review everything before committing. If you can't explain the code, don't commit it.
- Never include secrets, credentials, or PII in prompts.
- AI-generated code follows the same standards as hand-written code: same linting, same tests, same review process.
- AI can draft — humans own.

---

## 16. Infrastructure Provisioning

**Minimum Viable IaC**: The infrastructure is deliberately scoped to provision the Koyeb environment using Terraform, prioritizing backend reproducibility over complete infrastructure automation.

**Bootstrap Flow**:
1. Manual: Create external stateful resources (Supabase, Upstash Redis).
2. Export secrets to the local environment (`TF_VAR_*`).
3. Execute `terraform init` -> `terraform apply` in the `infrastructure/` directory.

---

*Last updated: v1.7.0*

---

## 📈 Implementation Plan: SRE Portfolio Refinement

This document defines the execution strategy to demonstrate engineering judgment under uncertainty. The core focus is technical honesty: real data (including noise), explicit trade-offs, and human friction.

> [!NOTE]
> **Time Expectation**: 10–12 weeks (part-time). Controlled execution to avoid scope creep.

### PROJECT STATUS

#### Phase 1: Hygiene and Benchmarks (✅ COMPLETED)

- [x] **1. Reproducible Benchmark (B1)**
  - **Tool**: k6 implemented with scripts in `/benchmarks/scripts/` (health.js, read_path.js, contact.js).
  - **Execution**: PowerShell runner (`benchmarks/run.ps1`) created to archive results per commit.
  - **Transparency**: README updated with Real Baseline and honest analysis of failures (SQLite vs Prod).

- [x] **2. Basic Security (A1)**
  - **Hygiene**: Swagger/ReDoc disabled conditionally in production.
  - **Validation**: Test suite added in `test_configuration.py` guaranteeing behavior.

- [x] **3. Coherent SRE Alerts (A2 Basic)**
  - **Objective**: Monitoring aligned with SLOs without over-design.
  - **Result**: Error alerts (5xx) separated from latency degradations. Metrics enriched with `app_version` for total traceability. Naming conventions standardized in English.

---

### UPCOMING PHASES

#### Phase 2: Credibility and Incidents (✅ COMPLETED)

> [!WARNING]
> **Strict Timebox and Scope**: Maximum 2 Case Studies. Writing and data extraction are slow; expanding scope here guarantees not finishing.

**Weekly Cadence**
- **Week 4**: Select 2 incidents + gather raw evidence.
- **Week 5**: Case Study #1 (draft + metrics + tags).
- **Week 6**: Case Study #2.
- **Week 7**: Normalize badges, confidence score, final review.

**Execution Risks & Mitigations**
- **Risk 1**: Data extraction takes longer than expected.
  - *Mitigation*: Freeze the time window (e.g., last 30 days) from Day 1.
- **Risk 2**: Writing expands uncontrollably or becomes generic.
  - *Mitigation*: Hard word limit (< 700 words) per case. Use summarized technical language only; strictly no "LinkedIn-style" phrasing.
- **Risk 3**: Lack of source traceability.
  - *Mitigation*: Mandatory evidence checklist before publishing.

- [x] **4. Case Studies (D1 + D2)**
  - **Max 2 Cases Rule**: Case A (mandatory, highest business impact); Case B (mandatory, best evidence of *human friction*). Everything else goes to the backlog (Phase 3+).
  - **Definition of "Done"**: A Case Study is ready ONLY if it has:
    - Narrative in < 700 words (concise technical language, zero generic/LinkedIn phrasing).
    - 3 "before vs after" metrics.
    - Real/Reproduced tag visible.
    - 1 lesson learned + 1 future action.
  - **Standard Template (Disciplined Copy/Paste)**:
    1. **Context**: Which service, when, impact.
    2. **Symptom**: What was observed.
    3. **Initial Hypotheses**: What was suspected.
    4. **Partial/Human Cause**: Decision, process, communication, etc.
    5. **Before vs After**: Table with 3 metrics.
    6. **Real vs Reproduced**: Data source and limitations.
    7. **Lessons & Guardrails**: Preventive action.

- [x] **5. Real vs Synthetic Signal (B2)**
  - **Labeling Rule**: Every chart/table must have a badge (in title or subtitle). No tag = no publish.
  - **Taxonomy**:
    - `REAL`: Verifiable production telemetry.
    - `REPRODUCED`: Controlled experiment replicating a pattern.
    - `SYNTHETIC`: Simulated data for demo purposes.
  - **Confidence Score**:
    - `High`: Real data + consistent evidence from ≥2 sources.
    - `Medium`: Real but incomplete, or strictly controlled reproduced data.
    - `Low`: Synthetic or insufficient sample.

#### Phase 3: Visual Consistency (Week 8)

> [!WARNING]
> **Non-negotiable Timebox**: 3–4 real days maximum. Focus on typography and reducing visual noise.

- [x] Premium aesthetic improvement focused on readability of technical data.

#### Phase 4: Closure and Release (Weeks 9-12)

- [x] Final smoke tests.
- [x] Technical release notes documenting accepted degradations.
- [x] Final hygiene check in production.