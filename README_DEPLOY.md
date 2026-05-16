# Portfolio Deployment Guide

Standard Operating Procedure for deploying the Full-Stack Portfolio with a focus on zero-cost, high performance, and permanent availability.

## 🚀 Backend Infrastructure (Koyeb)
Scalable Python API hosting.

1.  **Source**: Connect your GitHub repository.
2.  **Service Configuration**:
    *   **Root Directory**: `/` (Keep at root for monorepo Docker context)
    *   **Builder**: Select `Dockerfile`
    *   **Dockerfile location**: `backend/Dockerfile`
    *   **Instance Type**: `Nano` (512MB RAM - Permanent Free Tier)
    *   **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
    *   **Port Visibility**: Expose port `8000` (HTTP)
3.  **Environment Variables**:

    | Variable | Required | Description |
    |---|---|---|
    | `RESEND_API_KEY` | ✅ Yes | Resend API Key |
    | `ENVIRONMENT` | ✅ Yes | Set to `production` |
    | `DATABASE_URL` | ⭐ Recommended | PostgreSQL URL (e.g. Supabase pooled connection with `postgresql+asyncpg://...`). Falls back to SQLite if empty. |
    | `REDIS_URL` | ⭐ Recommended | Redis URL (e.g. `rediss://...`). Falls back to memory if empty. |
    | `SENTRY_DSN` | ⭐ Recommended | Sentry DSN for error tracking (see Sentry project settings) |
    | `SENTRY_TRACES_SAMPLE_RATE` | Optional | Transaction sample rate `0.0–1.0` (default: `0.2`) |
    | `OTLP_ENDPOINT` | Optional | OTLP endpoint for distributed traces (e.g. Grafana Cloud) |

---

## 💻 Frontend Interface (Vercel)
Global Edge UI deployment.

1.  **Source**: Connect the same GitHub repository.
2.  **Project Configuration**:
    *   **Framework Preset**: `Vite`
    *   **Root Directory**: `/frontend`
    *   **Build Command**: `npm run build`
    *   **Output Directory**: `dist`
3.  **Environment Variables**:
    *   `VITE_API_URL`: `https://api.argenisbackend.com/api/v1`
    *   `VITE_ENABLE_CHAOS_PLAYGROUND`: `true` (enables the Chaos Playground and Trace Viewer UI)
    *   **Live Status**: `https://api.argenisbackend.com/health` (JSON Health Check)

---

## 🛠️ Architecture Notes
*   **Database (PostgreSQL/SQLite)**: The system is designed for **Managed PostgreSQL** in production (recommended: **Supabase Postgres**) to ensure data persistence across container restarts. It gracefully falls back to **SQLite** if no `DATABASE_URL` is provided. We do **not** commit the database file to Git. Run `alembic upgrade head` during deploy/release tasks, not on every container boot.
*   **Active Security**: Built-in protection includes a 5-minute deduplication window, honeypot traps, and heuristic spam scoring.
*   **Instant Availability (Fixing the 15s Cold Start)**: Cloud platforms like Koyeb hibernate free web services, which causes a 10-15s cold start. To prevent this, configure an **external cron service** (like [cron-job.org](https://cron-job.org/en/)) to send a `GET` request to `https://api.argenisbackend.com/health` every **3 minutes**.
    > ⚠️ *Note*: GitHub Actions `cron` was previously used but is highly unreliable (often delayed in the queue up to 15+ minutes), defeating the purpose of a keep-alive ping. Always use a dedicated uptime service.

### Recommended Koyeb Deploy Flow
1. **Release task / pre-deploy**: `alembic upgrade head`
2. **One-off seed (only when static SQL data must be refreshed)**: `python backend/scripts/migrate_data.py`
3. **Runtime start command**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

This avoids running migrations and full reseeds on every cold start.

---

## 📊 Observability Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Health check (used by Koyeb probes) |
| `GET /metrics` | Prometheus metrics (request rate, latency P95/P99, error rate) |
| `X-Request-ID` header | Unique ID in every response for log correlation |
| `X-Trace-ID` header | OpenTelemetry trace ID for distributed tracing |

> **Note**: `/metrics` is publicly accessible on Koyeb at `https://<app>.koyeb.app/metrics`.
> For a portfolio this is acceptable. Add Basic Auth if you want to restrict access.

---

## 🔍 Local Monitoring Stack (Development)

To run Prometheus + Grafana + Jaeger locally:

```bash
# Uncomment the monitoring services in docker-compose.yml, then:
docker-compose up -d api prometheus grafana jaeger
```

| Service | URL | Credentials |
|---|---|---|
| Grafana Dashboards | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Jaeger UI | http://localhost:16686 | — |
| API Metrics | http://localhost:8000/metrics | — |

---
**Maintained by**: Argenis1412/portfolio
**Version**: 1.9.1 (UI/UX Resilience Overhaul — Mobile Navigation + Typography + Chaos Observability)
