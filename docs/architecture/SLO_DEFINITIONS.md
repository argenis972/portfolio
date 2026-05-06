# Service Level Objectives (SLOs)

> Single source of truth for system performance targets.
> Values extracted from ENGINEERING_PLAYBOOK.md section 11.

---

## Overview

This document defines the Service Level Objectives (SLOs) for the backend API. Each SLO includes the target value, measurement method, current status based on production incidents, and alert triggers.

---

## 1. Static Portfolio Data Endpoints

### Endpoints
- `GET /api/v1/about`
- `GET /api/v1/projects`
- `GET /api/v1/stack`
- `GET /api/v1/experiences`

### Latency Target
- **SLO:** P95 < 50ms

### Measurement Method
- **Primary:** Prometheus histograms exposed at `/metrics` endpoint (ADR-04)
- **Secondary:** Synthetic telemetry from frontend `useLiveMetrics` hook (ADR-13)
- **Backend Source:** FastAPI middleware records `latency_ms` per request with path label

### Current Status
- **Status:** ✅ BEING MET
- **Evidence:** INC-002 resolution (v1.4.1) migrated reads from PostgreSQL to `JSONRepository`. P95 dropped from ~320ms to <50ms.
- **Baseline:** Files loaded into memory at startup; no database round-trip

### Alert Trigger
- P95 > 50ms for 5 consecutive minutes
- OR error rate > 0.5% for 15 minutes

---

## 2. Contact Submission Endpoint

### Endpoint
- `POST /api/v1/contact`

### Latency Target
- **SLO:** P95 < 200ms (includes Redis round-trip for rate limiting)

### Measurement Method
- **Primary:** Prometheus histograms with `path="/api/v1/contact"` label
- **Secondary:** Frontend `TraceConsole` records end-to-end latency including network
- **Components Measured:** Redis rate limit check + PostgreSQL write + Resend API call

### Current Status
- **Status:** ✅ BEING MET
- **Evidence:** INC-001 resolution (v1.3.0) migrated rate limiting to Redis (Upstash). Counters survive container restarts.
- **Note:** Redis is now in the critical path; rate limiter fails open if unavailable (accepted in INC-001)

### Alert Trigger
- P95 > 200ms for 5 minutes
- OR 5xx error rate > 0.5% for 15 minutes
- OR Redis connection failures > 1% for 5 minutes
- **Structured log event:** `rate_limiter_redis_fallback_open` → configure as a
  critical alert in Sentry/Grafana. When this fires, anti-spam and rate limiting
  on `/contact` are non-functional (fail-open). See INC-001 / FAILURE_MODEL.md §1.

---

## 3. Health Check Endpoint

### Endpoint
- `GET /health`

### Latency Target
- **SLO:** P99 < 100ms *(Recalibrated from 20ms to match free tier hypervisor realities)*

### Measurement Method
- **Primary:** Prometheus histograms (no database dependency)
- **Secondary:** Keep-alive cron job pings every 14 minutes, logs response time
- **Chaos Testing:** Chaos Playground includes health check latency in telemetry

### Current Status
- **Status:** ⚠️ DEGRADATION OBSERVED
- **Evidence:** Benchmarks against production (commit 3775843) show a clear distinction between infrastructure states:
    - **P95 Cold Start:** ~3.5s (Initial container spin-up on Koyeb Free Tier).
    - **P95 Warm State:** ~1.3s (Steady state traffic, 5 concurrent VUs).
    - **Ramp-up Failure:** Timeouts observed at 20 concurrent VUs (Error rate ~9.7%), indicating infrastructure capacity limits.
- **Root Cause:** Primarily Koyeb Free Tier cold-starts and "noisy neighbor" latency on shared hypervisors. ADR-05 removal of DB dependency fixed the logic, but infra remains non-deterministic under load.
- **Historical Issue:** INC-002 showed keep-alive hitting `/health` was not enough when data endpoints still required DB.

### Alert Trigger
- P99 > 100ms for 3 minutes
- OR non-200 HTTP response for 2 consecutive checks
- OR keep-alive cron reports failure

---

## 4. Error Rate Objectives (Global)

### Target
- **SLO:** Maximum 0.5% 5xx error rate over any 15-minute rolling window

### Measurement Method
- **Source:** Prometheus counter `http_requests_total{status=~"5.."}` divided by total requests
- **Recording Rule:** `rate(http_requests_total[15m])` filtered by status code

### Current Status
- **Status:** ✅ BEING MET
- **Historical Peak:** INC-001 period had elevated errors due to rate limiter failures; resolved in v1.3.0

### Alert Trigger
- Error rate > 0.5% for 15 minutes (warning)
- Error rate > 2% for 5 minutes (critical)

---

## 5. Availability Objectives

### Target
- **SLO:** 99.9% availability for critical endpoints (data reads, health check)
- **Excluded:** Chaos Playground synthetic failures (labeled as expected behavior per ADR-13)

### Measurement Method
- **Source:** Synthetic probe success rate from keep-alive cron + frontend telemetry
- **Window:** 30-day rolling

### Current Status
- **Status:** ✅ BEING MET
- **Downtime Budget:** ~43 minutes/month allowed

### Alert Trigger
- Availability < 99.9% over 1-hour window

---

## References

- **Source of Truth:** ENGINEERING_PLAYBOOK.md section 11 (Performance)
- **Incident History:** CHANGELOG.md (INC-001 through INC-006)
- **Architecture Decisions:**
  - ADR-04: Protected Prometheus metrics
  - ADR-05: JSON-First Read Path
  - ADR-11: External Storage (Redis)
  - ADR-13: Synthetic vs. Real telemetry labeling
