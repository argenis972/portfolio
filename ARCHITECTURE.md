# 🏛️ Architecture & Technical Decisions

This document details the reasoning behind the architectural choices found in this repository. Since this is a personal portfolio showcasing engineering practices, it serves as a lightweight Architecture Decision Record (ADR).

## 1. Clean Architecture in the Backend
**Why?** The backend is structured using Clean Architecture (Controllers -> Use Cases -> Entities -> Adapters). While a "simple portfolio" might not strictly need it, demonstrating language-agnostic boundary isolation shows scaling potential and separation of concerns.

## 2. Decoupled Frontend and Strict API Consumer
**Why?** The React frontend never connects directly to a database, and the FastAPI backend does not serve HTML. Keeping these completely separate ensures proper CORS enforcement, prevents accidental tightly-coupled logic, and mirrors real-world enterprise architectures where mobile devices could consume the same backend.

## 3. Managed Database and One-Off Seeding
**Decision**: In production, the managed PostgreSQL database is not committed to Git and is not reseeded on every boot.
**Why?** Committing databases is an anti-pattern, and reseeding on every Koyeb cold start increases readiness time. Schema migrations should run during deploy/release steps, while `python backend/scripts/migrate_data.py` should be used as a one-off refresh task only when static SQL data needs to be rebuilt.

## 4. Observability and Protected Metrics
**Decision**: Exposing Prometheus metrics at `/metrics` but requiring Basic Auth in production.
**Why?** While the metrics are intentionally accessible to reviewers, exposing a public `/metrics` endpoint on the open internet (even for a portfolio) is a non-standard practice that could be seen as a security oversight. Adding `METRICS_BASIC_AUTH` ensures that only authorized clients (or reviewers with the provided credentials) can see the live stack's health, throughput, and latencies.

## 5. Performance: JSON-First Read Path
**Decision**: Prioritizing `JSONRepository` for all portfolio-related reads (about, projects, stack, etc.) in production.
**Why?** Using a managed PostgreSQL database for static data in a serverless/ephemeral environment adds significant cold-start latency and increases the risk of transient connection failures. By serving the portfolio data directly from memory-cached JSON files (Clean Architecture allows swapping adapters seamlessly), we achieve P95 latencies < 50ms and eliminate PostgreSQL as a single point of failure for the main application view. PostgreSQL remains reserved for transactional or future dynamic needs.

## 6. Security Regex over Allow-Lists
**Decision**: The CORS Policy uses a regex rule (`^https://argenisbackend\.com|https://portfolio.*-argenis1412s-projects\.vercel\.app$`) instead of exact strings or `*`.
**Why?** Vercel creates dynamic preview domains per PR. Doing hardcoded allowed lists blocks PR testing. Using a wide open `*` disables secure credential-passing. The precise regex allows only our generated subdomains to seamlessly interact with the API, blocking impersonation from other `*.vercel.app` sites.

## 7. Global Consistency: Unified English Codebase
**Decision**: Migrating all remaining Portuguese identifiers, including the `/saude` endpoint, to English (`/health`).
**Why?** Although the project started with some Portuguese core models, maintaining a bilingual codebase creates cognitive load and technical debt. We renamed all backend directories (`controladores` → `controllers`, etc.) to adhere to international industry standards.
*Status Update (v1.9.2):* The `/saude` and `/salud` endpoints are currently **deprecated** and kept alive strictly as fallback aliases with warning logs to prevent breaking legacy probes. Final removal is scheduled for `v1.9.3`.

## 8. Frontend State Architecture
**Decision**: React + TanStack Query instead of Redux/Zustand for most data mapping.
**Why?** A portfolio is a read-heavy application. TanStack Query treats remote data precisely as it is — a cache of server state. Local state is kept minimal, leaving data fetching, prefetching on hover, and cache invalidation entirely to the asynchronous fetching layer.

## 9. Full-Stack Error Tracking (Sentry)
**Decision**: Using Sentry for both React and FastAPI.
**Why?** Observability is more than just metrics; it's about context. Sentry provides the "why" behind failures, capturing breadcrumbs, request metadata, and stack traces that Prometheus metrics (`/metrics`) can't show. By using `VITE_SENTRY_DSN` on the frontend and `SENTRY_DSN` on the backend, we achieve unified error correlation across the entire user journey.

## 10. Security Hardening (Defense-in-Depth)
**Decision**: Implementing `SecurityHeadersMiddleware` and `GZipMiddleware`.
**Why?** Browsers rely on specific headers (HSTS, NoSniff, X-Frame-Options) to enforce security policies. While the frontend had these in Vercel, the backend API was unprotected if accessed directly. Adding these headers at the middleware level ensures that every response is hardened by default. Additionally, GZip compression for payloads >1KB significantly improves UI performance on low-bandwidth networks.

## 11. External Storage for Distributed State
**Decision**: Migrating Rate Limiting and Persistence from local Memory/SQLite to Redis and PostgreSQL for production.
**Why?** In "ephemeral" cloud environments like Koyeb, local file storage (SQLite) and in-memory caches (Rate limiting counters) are wiped on every container restart. By decoupling state into managed PostgreSQL (recommended: Supabase via `asyncpg`) and Redis (via `Upstash`), the application achieves true horizontal scalability and persistent antispam protection across multiple replicas.

## 12. Future Strategy: Scalability via Multi-Deploy (FastAPI & Go)
**Decision**: A full rewrite of the backend to Go is officially discarded as over-engineering. Instead, any future expansion will follow a **multi-deploy strategy**: keeping Python (FastAPI) for the primary endpoints and expanding with Go only for specific, high-performance microservices.
**Why?** Currently, the system is stable, P95 latency is < 50ms, and error rates are exceptionally low. The only previous penalty was cold starts, which was efficiently resolved with a cron-based keep-alive strategy. The true bottleneck is the hardware limitation of the Koyeb free tier, a constraint that no language change can magically fix.
Migrating entirely to Go simply to gain speed before a real problem exists is an anti-pattern. That approach introduces more infrastructure, more points of failure, and less clarity, all to fix something that is already working perfectly.
If Go is integrated in the future, it will only be under real necessity signals (e.g., CPU constantly saturated, P95 rising under load, or heavy concurrent tasks) following this intelligent workflow:
1.  **Create a minimal Go service** (e.g., isolated deploy) for specific tasks.
2.  **FastAPI acts as the consumer** (`Client -> FastAPI -> Go Service`).
3.  **Measure** the real latency, consumption, and added complexity before deciding to expand further.

## 13. Frontend Observability Enhancements
**Decision**: Enhanced frontend observability with real-time telemetry, failure visibility, and end-to-end traceability.
**Why?** To provide engineers with actionable insights into system behavior, making failure/recovery visible and ensuring strong correlation in logs.
- Added MetricsSparkline component with linear line, threshold lines, and vertical incident markers for real-time P95 latency telemetry.
- Extended useLiveMetrics hook to keep timestamped samples, baseline P95, recent traces, latest event, circuit-breaker and timeout states.
- Rewrote LiveMetricsBento to show delta vs previous, delta vs baseline, failure-model panel, and telemetry timeline.
- Updated Hero sidecar to render real sparkline, circuit state, and latest trace.
- Modified ChaosPlayground to emit trace_id and include richer log fields (retry_triggered, circuit_breaker, timeout_ms).
- Enhanced TraceViewer and LogStream to display both request_id and trace_id for end-to-end correlation.
- Fixed LogStream auto-scroll to stay inside the terminal and removed global window.scrollTo in App.tsx.
- Added missing i18n keys for metrics, failure model, and telemetry legend.

## 14. Modular Frontend API & Component Decomposition
**Decision**: Restructuring the monolithic `api.ts` into a layered `src/api/` directory and decomposing large UI components into focused hooks and sub-components.
**Why?** As the frontend complexity grew, the single `api.ts` file became a bottleneck for readability and type safety. Moving to a modular structure (`client`, `schemas`, `services`) ensures better separation of concerns. Similarly, extracting logic into custom hooks (`useChaosActions`, `useContactForm`) and UI into atomic components (`ChaosTerminal`, `ChaosActionCard`) improves testability and adheres to the Single Responsibility Principle.

## 15. Production Resilience & Infrastructure Hardening

Building for production introduced real-world challenges that were addressed with SRE principles:

### 15.1 Resilient Chaos Persistence
**Decision**: Chaos actions (latency, spikes) must not depend on database availability to complete their primary task (the simulation).
**Implementation**: We implemented a "Fail-Silent" pattern in `chaos.py`. If the database fails to record an incident (due to missing tables or connection issues), the system logs the error but continues the chaos simulation. This ensures the playground remains functional even under partial infrastructure failure.

### 15.2 Monorepo Build Standardization
**Decision**: Unify build context for Docker across all environments (Koyeb, GitHub Actions, Local).
**Implementation**: The `Dockerfile` is designed to be "Root-Aware". By building from the repository root and using prefixed `COPY` commands (e.g., `COPY backend/requirements.txt`), we eliminate path mismatches between different CI/CD runners.

### 15.3 Security Header & CORS Synchronization
**Decision**: Use a single source of truth for allowed origins and strictly sync CSP with production subdomains.
**Implementation**:
- **CORS**: Managed via Regex in `settings.py` to support dynamic subdomains (api.*, www.*).
- **CSP**: Implemented in `vercel.json` to explicitly whitelist `api.argenisbackend.com`, preventing browser-level blocks during frontend-backend communication.

## 16. Internationalization (i18n) & API Contracts
**Decision**: Enforce "English-First" API contracts while maintaining multi-language content.
**Reasoning**: All internal identifiers, routes, and database keys were migrated from Portuguese to English to ensure the codebase follows global engineering standards, while still serving localized content via the `/api` responses.

## 17. SRE Alerting Coherence (A2 Basic)
**Decision**: Separating Error Rate alerts from Latency alerts and optimizing histogram buckets for SLO tracking.
**Why?** Generic "High Latency" alerts that actually trigger on 5xx errors (the previous state) create noise and confuse incident response. By separating them, we achieve:
1. **Actionable Alerts**: `HighErrorRate` points to code bugs or database failures; `HighLatencyP95` points to resource exhaustion or N+1 queries.
2. **SLO Alignment**: Histogram buckets in the backend are now explicitly set to `[50ms, 200ms, ...]` to match the P95 targets defined in the Engineering Playbook.
3. **Traceability**: All alerts and metrics now include `app_version` as a label, allowing instant correlation between a new deployment and a performance degradation.

## 18. Chaos E2E Testing Strategy
**Decision**: Executing Chaos E2E tests against a local `docker-compose` environment in CI rather than production/staging, and preserving `/health` endpoint availability (`200 OK (Degraded)`) during simulated failures.
**Why?**
1. **Trade-off**: CI tests validate system behavior deterministically (local environment). They do not simulate real network conditions or provider-level variability. This ensures the CI is 100% reproducible and avoids network flakiness.
2. **Semantics of /health**: During a `FAILURE` scenario, returning `503` would cause the orchestrator (Koyeb) to kill and restart the container, defeating the "Fail-Silent" pattern. Returning `200 OK (Degraded)` ensures the system survives and continues serving cached portfolio data. *200 OK does not imply full system health. It indicates the service is still serving responses under degraded conditions.*

## 19. Infrastructure as Code Strategy
**Decision**: Provisioning a Minimum Viable IaC setup with Terraform, strictly scoped to the Koyeb application and environment variables, while intentionally leaving third-party stateful services (Upstash Redis, Supabase) as manual steps.
**Why?** This setup prioritizes reproducibility of the backend service, not full infrastructure parity. Automating the free-tier setups of external providers often requires complex modules or unsupported providers, violating the goal of a clear, readable codebase. By provisioning only Koyeb, any developer can understand the deployment topology in 5 minutes and bootstrap the backend with `< 10 commands`.

## 20. Resilient Background Processing (Redis Streams)
**Decision**: Migrating from in-process volatile background tasks to a durable worker based on Redis Streams with explicit error classification and PEL recovery.
**Why?** In Phase 3 (Operational Health), we transitioned from "best effort" task processing to "at-least-once" delivery. This ensures no contact submissions are lost due to transient provider failures or process restarts.
- **Error Classification**: The worker distinguishes between transient (retry with backoff), permanent (DLQ), and unknown errors, preventing "poison pill" messages from blocking the queue.
- **Self-Healing (XAUTOCLAIM)**: By scanning the Pending Entries List (PEL) at startup, the worker can automatically recover jobs that were assigned to a previous instance that crashed.
- **Observability**: Real-time visibility into queue depth, retry rates, and DLQ size through Prometheus metrics, allowing proactive incident response before users report issues.
- **Resilient Testing**: To maintain CI speed and stability, we use a "force-memory" strategy in tests, mocking Redis behavior while strictly validating the state machine logic of the worker.

## 21. UI/UX Resilience & Observability
**Decision**: In the TraceViewer and ChaosPlayground, a simulated "Latency Injection" explicitly emits a `503 ERR` trace rather than `200 OK`, even though the backend successfully handled the chaos request itself.
**Why?** This demonstrates realistic system behavior and circuit breaker patterns. A timeout in a highly available architecture is an error that should trigger fallback mechanisms, not just a "slow success". Emitting a `503` in the observability trace proves the monitoring system can correctly identify SLA breaches and SLA-driven failure states.
