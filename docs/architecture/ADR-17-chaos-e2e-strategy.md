# ADR-17: Chaos E2E Testing Strategy

**Status:** Accepted
**Date:** 2026-05-04
**Version:** v1.7.0

## Context

The backend implements a Chaos Playground designed to simulate degradation (latency spikes, dependency failures, circuit breaker trips). While unit and integration tests verify the individual components of this system, there was no automated mechanism to prove that the system as a whole degrades gracefully and recovers automatically under real failure conditions.

## Decision

We will execute Chaos E2E tests against a local `docker-compose` environment in CI (GitHub Actions) on a weekly basis, rather than testing against production or staging environments.

Additionally, the `/health` endpoint behavior is explicitly defined to return `200 OK (Degraded)` instead of `503 Service Unavailable` during simulated failure scenarios.

## Rationale & Trade-offs

1. **Trade-off (Local vs Real Environment):** CI tests validate system behavior deterministically in a local environment. They do not simulate real network conditions or provider-level variability. This trade-off ensures the CI is 100% reproducible and avoids pipeline flakiness caused by external factors, while still proving the application logic behaves correctly under stress.
2. **Semantics of `/health`:** During a `FAILURE` scenario (e.g., database is down), returning `503` would cause the orchestrator (Koyeb/Kubernetes) to kill and restart the container. This defeats the purpose of the "Fail-Silent" pattern, where the system is supposed to continue serving cached portfolio data despite database unavailability.
3. **Redefining Health:** `200 OK` does not imply full system health. It indicates the service is still serving responses under degraded conditions. The response payload explicitly details the failure: `{"status": "degraded", "dependencies": {"db": "down"}}`.

## Consequences

- **Positive:** We have automated proof that the system survives the failure scenarios it claims to handle.
- **Positive:** The fail-silent architecture is protected from aggressive orchestrator restarts.
- **Negative:** The CI tests do not capture issues specific to Koyeb's infrastructure or Supabase network partitioning.
