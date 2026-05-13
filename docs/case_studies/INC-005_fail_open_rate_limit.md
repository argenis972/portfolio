# Case Study: INC-005 (Fail-Open Rate Limiting & IP Spoofing)

**Confidence Score**: `High` (Audit findings & architectural review)
**Tag**: `REPRODUCED`

### 1. Context
- **Service**: Backend API (FastAPI) and Rate Limiting Infrastructure (Redis).
- **Timeline**: Security & Resilience Audit (v1.x).
- **Impact**: Potential 100% exposure to spam and abuse during Redis outages or via IP spoofing.

### 2. Symptom
During an infrastructure resilience audit, it was discovered that the rate-limiting mechanism (`slowapi` + Redis) was configured to fail **open**. If Redis went down or timed out, the system would catch the exception, log a warning, and allow the request to proceed. Concurrently, the IP extraction logic implicitly trusted `X-Forwarded-For` without validating the upstream proxy.

### 3. Initial Hypotheses
The original implementation prioritized availability over security. The assumption was that rejecting requests due to an internal cache failure would degrade user experience, so failing open seemed like a reasonable fallback.

### 4. Partial/Human Cause
Lack of distinction between read-only and mutating endpoints. The fail-open strategy is valid for fetching portfolio data (`GET /projects`), but applying the same fallback to the `/contact` endpoint created a Single Point of Failure (SPOF) for abuse. The IP spoofing vulnerability was caused by a default configuration that trusted standard proxy headers without a definitive allowlist.

### 5. Before vs After [REPRODUCED]

| Metric | Before (v1.x) | After (Security Phase 1) |
| :--- | :--- | :--- |
| **Contact API Behavior on Redis Failure** | 200 OK (Fail-Open) | 503 Service Unavailable (Fail-Closed) |
| **Read-Only API Behavior on Redis Failure** | 200 OK (Fail-Open) | 200 OK (Fail-Open) |
| **IP Spoofing Vulnerability** | High (Trusted `X-Forwarded-For`) | Mitigated (`strict_proxy_mode` allowlist) |

### 6. Real vs Reproduced
- **Source**: `REPRODUCED`.
- **Limitations**: The vulnerability was discovered and patched proactively during an audit. Simulated in tests via `monkeypatch` on the `limiter.hit` function to trigger connection errors.

### 7. Lessons & Guardrails
- **Lesson**: Availability must be endpoint-specific. Mutating or sensitive endpoints must fail closed to protect the system, while read-only endpoints should degrade gracefully and fail open to maintain user experience.
- **Guardrail**: Implemented strict routing separation for fail-closed behaviors (`FAIL_CLOSED_PATHS`). Added a Prometheus metric (`rate_limit_backend_unavailable_total`) to alert on Redis degradation before it causes widespread 503s. Introduced `strict_proxy_mode` as an environment feature flag to secure IP extraction.
