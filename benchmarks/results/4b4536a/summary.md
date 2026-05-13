# Benchmark Results - commit 4b4536a

**Timestamp:** 2026-05-09T00-15-37
**Base URL:** https://api.argenisbackend.com
**k6 version:**

## Results

| Script | Status | Notes |
|--------|--------|-------|
| `health` | [WARN] THRESHOLD BREACH | See health.json | | `read_path` | [WARN] THRESHOLD BREACH | See read_path.json | | `contact` | [WARN] THRESHOLD BREACH | See contact.json |

**0/3 scripts passed all thresholds.**

> [WARN] 3 script(s) breached thresholds - review .json files for the degradation point. This is expected in stress scenarios.

## How to reproduce

\\\powershell
# Start backend first:
cd backend
uvicorn app.main:app --port 8000

# Then run benchmarks:
.\benchmarks\run.ps1 -BaseUrl http://localhost:8000
\\\

## Notes on data

- Results labeled `load_test_reproduced` are not real production traffic.
- Results labeled `baseline_real` (when available) are from production monitoring.
- Stress scenarios are intentionally designed to breach thresholds - the goal is to find the degradation point, not to always pass.
- Run each script 2-3 times and compare: if p99 varies >30%, the environment is noisy (Koyeb is not deterministic).
