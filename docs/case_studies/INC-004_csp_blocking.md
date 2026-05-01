# Case Study: INC-004 (CSP Blocking)

**Confidence Score**: `High` (Real production data: browser console logs, Vercel edge telemetry).
**Tag**: `REAL`

### 1. Context
- **Service**: Frontend (Vercel) and Backend (Koyeb) integration.
- **Timeline**: v1.3.x to v1.4.0 (Production domain cutover).
- **Impact**: 100% failure rate for all client-side API requests in the production environment.

### 2. Symptom
Upon accessing the production domain (`argenisbackend.com`), the browser actively blocked all API network requests. The browser console explicitly reported Content Security Policy (CSP) violations, specifically restricting the `connect-src` directive.

### 3. Initial Hypotheses
Assumed the backend CORS policy in Koyeb was rejecting the requests from the new frontend custom domain.

### 4. Partial/Human Cause
Infrastructure silos and environmental drift. The frontend and backend managed security headers independently without a single source of truth. The incident bypassed QA because `localhost` and Vercel preview URLs (staging) utilized relaxed CSP templates. The restrictive production CSP was only evaluated post-cutover.

### 5. Before vs After

| Metric | Before (Production Cutover) | After (v1.4.0) |
| :--- | :--- | :--- |
| **API Client Success Rate** | 0% | 100% |
| **Header Configuration** | Desynced (Siloed configs) | Synced (`vercel.json` + `settings.py`) |
| **CORS Preflight Failures**| N/A (Blocked client-side) | 0 |

### 6. Real vs Reproduced
- **Source**: `REAL`.
- **Limitations**: Sourced directly from production incident logs. The failure occurred before backend ingestion, meaning standard backend metrics recorded 0 traffic.

### 7. Lessons & Guardrails
- **Lesson**: Environment parity must strictly include security headers. Validating against staging environments with relaxed CSP/CORS profiles yields false positive deployment confidence.
- **Guardrail**: Established explicit configuration synchronization (ADR-15.3). Modifying `connect-src` in `vercel.json` mandates a matching update to the CORS regex in `settings.py`. Added automated `OPTIONS` preflight assertions in the CI pipeline.
