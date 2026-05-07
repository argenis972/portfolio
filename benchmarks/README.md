# Benchmarks

Load testing scripts using [k6](https://k6.io/) to measure and track API performance over time.

## Why this exists

Performance claims without data are marketing. This directory provides reproducible evidence that the system meets its SLOs — and documents *where* it degrades under stress.

Results are archived per git commit so regressions are detectable over time.

## Structure

```
benchmarks/
├── scripts/
│   ├── health.js       # GET /health — SLO: P99 < 100ms
│   ├── read_path.js    # GET /about, /projects, /stack — SLO: P95 < 50ms
│   └── contact.js      # POST /contact — SLO: P95 < 200ms (write path + anti-abuse)
├── results/
│   └── {commit}/
│       ├── health.json
│       ├── read_path.json
│       ├── contact.json
│       └── summary.md
└── run.ps1             # Runner: executes all scripts and archives results
```

## Quick Start

```powershell
# 1. Start the backend
cd backend
uvicorn app.main:app --port 8000

# 2. Run all benchmarks (separate terminal)
.\benchmarks\run.ps1

# 3. Run against production
.\benchmarks\run.ps1 -BaseUrl https://api.argenisbackend.com

# 4. Run a single script
.\benchmarks\run.ps1 -Script health

# 5. Dry run (no files saved)
.\benchmarks\run.ps1 -NoSave
```

## SLO Targets

| Endpoint | Metric | Target | Source |
|----------|--------|--------|--------|
| `/health` | P99 | < 100ms | SLO_DEFINITIONS.md |
| `/about`, `/projects`, `/stack` | P95 | < 50ms | SLO_DEFINITIONS.md |
| `/contact` | P95 | < 200ms | SLO_DEFINITIONS.md |
| All endpoints | Error rate | < 1% (5xx) | SLO_DEFINITIONS.md |

## Reading Results

Each script produces a `.json` file with raw k6 metrics and a structured `handleSummary` output.

Key fields to look at:
- `p(95)` and `p(99)` — distribution tails, not averages
- `max` — the worst case (often reveals outliers from cold starts)
- `error_rate` — 5xx rate during the run
- `data_label` — `"baseline_real"` vs `"load_test_reproduced"` (explicit about data origin)

## Important Notes on Reproducibility

**Environments are not perfectly deterministic.**

- Koyeb (production) has variable CPU allocation and network jitter
- Local results will differ from production — document both separately
- Run each benchmark 2–3 times; if P99 varies > 30%, the environment is noisy — say so in the summary

**Stress scenarios are designed to breach thresholds.**

`read_path.js` and `contact.js` include stress scenarios that push VU count beyond what the system comfortably handles. A threshold breach in a stress scenario is *expected behavior* — the goal is to document the degradation point, not to always pass.

## Known Trade-offs (documented, not hidden)

| Decision | Gain | Cost |
|----------|------|------|
| JSON-first read path | P95 latency < 50ms (vs 280-400ms before, INC-002) | Memory overhead per worker under high VU count |
| Redis anti-abuse stack | Rate limiting survives server restarts | +15–40ms per `/contact` request (Redis round-trip) |
| ETag caching | Zero-bandwidth revalidation (304) | Added complexity in conditional GET logic |
