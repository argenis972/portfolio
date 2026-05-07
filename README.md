# 🏛️ Cloud-Native Backend: Resiliency & Infrastructure Laboratory

[![License: MIT](https://img.shields.io/badge/License-MIT-gold.svg)](LICENSE)
[![Backend CI](https://github.com/Argenis1412/portfolio/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/Argenis1412/portfolio/actions)
[![Frontend CI](https://github.com/Argenis1412/portfolio/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/Argenis1412/portfolio/actions)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)

## 🌐 Live Demo
**Frontend:** [argenisbackend.com](https://argenisbackend.com) · **API Status:** [Healthy (JSON)](https://api.argenisbackend.com/health)

---

A **Cloud-Native payment backend** focused on resiliency, idempotency, and infrastructure automation. This isn't just a portfolio; it's a system built to survive and be managed at scale:

- 🏗️ **Infrastructure as Code (IaC)** — Fully managed via Terraform with automated CI/CD provisioning.
- 🌪️ **Chaos-Tested** — Automated weekly E2E stress tests to verify degradation and recovery.
- ✅ **Secret-First Orchestration** — All environment variables managed as Koyeb Secrets for maximum security.
- ✅ **Observability stack** — Sentry + Prometheus + OpenTelemetry for full system transparency.
- ✅ **Multi-layer anti-abuse** — Honeypot + Spam Scoring + Redis-backed deduplication + Rate Limiting.
- ✅ **JSON-First Read Path** — Eliminates Database cold-starts for public-facing data.
- ✅ **React 19 + TanStack Query** — Optimized frontend with zero-refetch and 15min caching.

---

## 🔄 Evolution: How This System Grew

This project didn't start production-ready. It evolved through real production incidents:

| Version | Milestone | Key Change |
|---|---|---|
| **v1.5.0** | Chaos Engineering | Deterministic chaos presets + stateful decision engine (ADR-14) |
| **v1.5.1** | Honest Telemetry | Synthetic vs. real labels + confidence indicator (ADR-13) |
| **v1.6.0** | Build Standardization | Modular API layer + root-context Dockerfile (ADR-15.2) — fixed INC-005 |
| **v1.7.0** | SRE Evidence | Minimum Viable IaC (Terraform) + Weekly Chaos CI (ADR-17/18) |
| **v1.8.0** | System Closure | Typography audit + Anti-spam accuracy fix (INC-006) |

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## 🏗️ Infrastructure & Reliability
This project follows a **Failure-Resilient** deployment model where infrastructure is treated as code.

- **Terraform-Managed Infrastructure**: Every resource (App, Service, Domain, Secrets) is provisioned via HCL code.
- **Secret-First Orchestration**: By-passing provider limitations through a pivot to Koyeb Secrets vault for all configuration.
- **Resilient Provisioning**: CI/CD pipelines that automatically filter missing/optional secrets to prevent deployment locks.
- **HCP Terraform Local Execution**: Optimized execution boundary where secrets are injected safely via GitHub Actions runners.
- **Automated Chaos E2E**: Weekly suites validating system survival during simulated dependency failures.

## 🧠 Engineering Highlights

### 🔐 Security Decisions
- **DDoS Protection**: Multi-layer rate limiting enforced per IP, email, and fingerprint.
- **Bot Mitigation**: Silent honeypot rejection without revealing detection to attackers.
- **State Resilience**: Idempotency keys prevent duplicate executions on network retries.
- **API Hardening**: HSTS, NoSniff, and strict CORS regex mapping to ephemeral environments.

| Decision | ADR | Rationale |
|---|---|---|
| Rate limiting enforced at middleware layer | ADR-10 | Ensures limits apply before business logic execution |
| Idempotency required for contact endpoint | ADR-11 | Prevents duplicate side-effects during network retries |
| CORS via regex, not allowlist | ADR-06 | Secures Vercel dynamic preview domains without wildcard `*` |
| Metrics endpoint behind Basic Auth | ADR-04 | Prevents public intelligence gathering on system health |

### 1. JSON-First & Scalable Persistence
[Architecture Decision Record: JSON-First Read Path](docs/architecture/JSON_FIRST_READ_PATH.md)

### 2. HTTP Caching Strategy
[Architecture Decision Record: HTTP Caching](docs/architecture/HTTP_CACHING.md)

### 3. Automated Quality Gate
- **Static Analysis**: `ruff` for linting/formatting and `mypy` for gradual typing.
- **CI/CD**: 80% coverage threshold enforced on every push — no exceptions.
- **Dockerized Builds**: Verified in CI, not just locally.

### 4. Observability & Chaos Control
[Architecture Decision Record: Observability](docs/architecture/observability.md)
- Stateful decision engine with hysteresis-based threshold monitoring
- Deterministic chaos presets (MILD, STRESS, FAILURE) for reproducible failure analysis
- Honest telemetry overlay distinguishing synthetic vs. real samples with confidence indicator
- **Automated Chaos CI**: Weekly E2E suite validating real system recovery times (ADR-17)

> [!TIP]
> **Latest Chaos CI Run**: [![Chaos E2E](https://github.com/Argenis1412/portfolio/actions/workflows/chaos-e2e.yml/badge.svg)](https://github.com/Argenis1412/portfolio/actions/workflows/chaos-e2e.yml)
> *The system is automatically stressed every Monday to verify it still degrades and recovers as advertised.*

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI · Pydantic V2 · structlog · slowapi · **Sentry** |
| **Frontend** | React 19 · TypeScript · Vite · TanStack Query · Tailwind CSS v4 · **Sentry** · Framer Motion |
| **Testing** | Pytest (Resilience + Perf + Chaos) · Vitest + Testing Library |
| **CI/CD** | GitHub Actions (Lint + Test + Build + E2E Chaos) |
| **Data** | **JSON/Memory** (Read Path) · **PostgreSQL** (DB) · **Redis** (Upstash) |
| **Deployment** | Koyeb (Backend via Dockerfile) · Vercel (Frontend) · Terraform (IaC) |
| **Performance & DX** | Predictive prefetching, background sync, scalable i18n (PT/EN/ES) |

---

## 📊 Production Incident Track Record
*8 real production incidents documented with post-mortems:*

| Incident | Failure | Detection | Resolution |
|---|---|---|---|
| **INC-001** | Rate limiter silently disabled (in-memory reset) | Manual discovery | Redis-backed rate limiting (v1.3.0) |
| **INC-002** | Cold start latency 280-400ms despite keep-alive | Metrics gap | JSON-First Read Path (v1.4.1) |
| **INC-003** | Chaos Playground crash on DB unavailability | Manual testing | Fail-silent persistence (v1.4.x) |
| **INC-004** | CSP blocking all API calls in production | Browser console | CSP/CORS synchronization (v1.4.0) |
| **INC-005** | Docker build context mismatch across environments | CI/CD failure | Root-context standardization (v1.6.0) |
| **INC-006** | Spam filter false positive on mixed-protocol links | Static analysis | Unified URL hostname normalization (v1.8.0) |
| **INC-007** | Koyeb Terraform Provider Schema Incompatibility | API 400 Bad Request | [Architectural pivot to Secret-First Orchestration](docs/architecture/INCIDENT_KOYEB_TERRAFORM.md) |
| **INC-008** | Destructive IaC Migration (Free Tier Constraints) | 14-hour Downtime | [Cold migration for operational consistency](docs/architecture/INCIDENT_DESTRUCTIVE_IAC_MIGRATION.md) |

See [FAILURE_MODEL.md](docs/architecture/FAILURE_MODEL.md) for full degradation behaviors and governing ADRs (INC-001–INC-008).

---

## 📊 Performance Baseline (SLO Targets)
*From [SLO_DEFINITIONS.md](docs/architecture/SLO_DEFINITIONS.md) — targets calibrated against production (Koyeb + PostgreSQL):*

| Endpoint | SLO Target | Benchmark Result |
|----------|-----------|------------------|
| `/about`, `/projects`, `/stack` | P95 < 50ms | [local baseline: ~820ms P95](benchmarks/results/02c08d3/summary.md) — SQLite/single-worker; prod run pending |
| `/contact` | P95 < 200ms | **P95 = 37ms** ✅ (local, in-memory anti-abuse stack) |
| `/health` | P99 < 100ms | **P95 Cold: ~3.5s** (infra spin-up) / **P95 Warm: ~1.3s** (shared hypervisor) |
| Error Rate | < 0.5% 5xx | **0%** (steady) / **~9%** (ramp-up DoS) — Koyeb Free Tier limits observed ✅ |

> See [`benchmarks/results/02c08d3/summary.md`](benchmarks/results/02c08d3/summary.md) for full analysis including why local breaches are expected.
> Reproduce: `k6 run --env BASE_URL=https://api.argenisbackend.com benchmarks/scripts/health.js` 

---

## 🌪️ Chaos Engineering (E2E in CI)

The resilience of the system is automatically verified in GitHub Actions. The CI pipeline spins up the backend and triggers intentional degradation to ensure the system survives and recovers automatically.

**Latest Chaos CI Run:**
```text
MILD → PASS
Latency spike: +320ms
Recovery: 4.2s

STRESS → PASS
Circuit breaker: OPEN → CLOSED
Recovery: 8.1s

FAILURE → PASS
Dependencies down (DB, Redis)
Service: still serving (fail-silent)
```

---

## 🚀 Quick Start

### Using Docker (Recommended)
```bash
git clone https://github.com/Argenis1412/portfolio.git
cd portfolio
docker-compose up --build
```

### Manual Setup
```bash
# Backend
cd backend
py -3.12 -m venv .venv && .venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install && npm run dev
```

> Run database migrations as part of deploy/release automation, not on every Koyeb application boot.
> 
> **Note**: Interactive documentation (Swagger/ReDoc) is disabled in production for security. To view the API contract, run the project locally in `development` mode and access `localhost:8000/docs`.

---

## 🧪 Tests

```bash
# Backend — with coverage
cd backend && pytest --cov=app --cov-config=.coveragerc --cov-report=html

# Frontend
cd frontend && npm run test
```

Key tests that demonstrate production-level reliability:
- ✅ **Persistent Anti-Spam**: Duplicate messages are blocked even after server restart (Redis → in-memory fallback).
- ✅ **Distributed Rate Limiting**: Limits enforced per email, per IP, and per browser fingerprint.
- ✅ **Honeypot Resilience**: Silent drop of bot submissions without revealing protection mechanisms.
- ✅ **Clean Architecture Boundary**: Automated checks — domain logic has zero dependencies on infrastructure.
- ✅ **Redis Failure Fallback**: `IdempotencyStore` and `SpamDedupStore` both fall back to memory if Redis is unreachable.
- ✅ **Concurrent Idempotency**: A second in-flight request with the same key receives HTTP 409 Conflict.

---

## 📁 Repository Structure
```
portfolio/
├── backend/              # FastAPI backend (Clean Architecture)
├── frontend/             # React 19 + TypeScript frontend
├── docs/
│   └── architecture/
│       ├── SLO_DEFINITIONS.md    # Per-endpoint SLOs with measurement methods
│       └── FAILURE_MODEL.md      # Production incident failure model (INC-001–INC-008)
├── .github/              # GitHub Actions CI/CD workflows
├── ARCHITECTURE.md       # ADR-01 through ADR-16
├── CHANGELOG.md          # Release history + 8 production incidents
├── ENGINEERING_PLAYBOOK.md  # SLOs, standards, incident protocol
└── docker-compose.yml
```

For more details: [`backend/README.md`](backend/README.md) · [`frontend/README.md`](frontend/README.md)

---

## 👨‍💻 Author

**Argenis Lopez** — Backend Developer · [LinkedIn](https://www.linkedin.com/in/argenis1412/) · [GitHub](https://github.com/Argenis1412)

---

## 📜 License
Licensed under the [MIT License](LICENSE).