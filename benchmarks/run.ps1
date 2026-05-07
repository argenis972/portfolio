# Benchmark Runner
#
# Runs all k6 benchmark scripts against a target URL and archives results
# per git commit. Designed to be simple and reproducible - no external deps.
#
# Usage:
#   .\benchmarks\run.ps1                          # runs against localhost:8000
#   .\benchmarks\run.ps1 -BaseUrl https://api.argenisbackend.com
#   .\benchmarks\run.ps1 -Script health           # single script only
#
# Output:
#   benchmarks/results/{commit}/health.json
#   benchmarks/results/{commit}/read_path.json
#   benchmarks/results/{commit}/contact.json
#   benchmarks/results/{commit}/summary.md        # human-readable summary

param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$Script = "all",    # "all", "health", "read_path", "contact"
    [switch]$NoSave             # run without saving results (dry-run)
)

$ErrorActionPreference = "Stop"

# --- Setup ---
$commit = (git rev-parse --short HEAD 2>$null)
if ([string]::IsNullOrWhiteSpace($commit)) {
    $commit = "no-git"
}
$timestamp = (Get-Date -Format "yyyy-MM-ddTHH-mm-ss")
$resultsDir = "benchmarks\results\$commit"
$scriptsDir = "benchmarks\scripts"

Write-Host ""
Write-Host "=== k6 Benchmark Runner ===" -ForegroundColor Cyan
Write-Host "  Base URL : $BaseUrl"
Write-Host "  Commit   : $commit"
Write-Host "  Results  : $resultsDir"
Write-Host "  Timestamp: $timestamp"
Write-Host ""

# Check k6 is available
if (-not (Get-Command k6 -ErrorAction SilentlyContinue)) {
    Write-Error "k6 not found. Install: winget install k6"
    exit 1
}

# Verify server is reachable before burning time on a full run
Write-Host "Checking server reachability..." -ForegroundColor Yellow
try {
    $healthCheck = Invoke-WebRequest -Uri "$BaseUrl/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "  Server OK (HTTP $($healthCheck.StatusCode))" -ForegroundColor Green
} catch {
    Write-Error "Cannot reach $BaseUrl/health - is the backend running?"
    exit 1
}

# Create results directory
if (-not $NoSave) {
    New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
}

# --- Run scripts ---
function Run-Benchmark {
    param([string]$Name)

    $scriptPath = "$scriptsDir\$Name.js"
    if (-not (Test-Path $scriptPath)) {
        Write-Warning "Script not found: $scriptPath - skipping"
        return
    }

    Write-Host ""
    Write-Host "--- Running: $Name ---" -ForegroundColor Cyan

    $outPath = "$resultsDir\$Name.json"
    $k6Args = @(
        "run",
        "--env", "BASE_URL=$BaseUrl",
        "--summary-trend-stats", "p(50),p(95),p(99),max,min",
        "--out", "json=$outPath",
        $scriptPath
    )

    if ($NoSave) {
        # Dry run: don't write JSON output
        $k6Args = @(
            "run",
            "--env", "BASE_URL=$BaseUrl",
            "--summary-trend-stats", "p(50),p(95),p(99),max,min",
            $scriptPath
        )
    }

    & k6 @k6Args
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-Warning "$($Name): k6 exited with code $exitCode (thresholds may have failed - check results)"
    } else {
        Write-Host "  $($Name): passed all thresholds" -ForegroundColor Green
    }

    return $exitCode
}

$scripts = if ($Script -eq "all") { @("health", "read_path", "contact") } else { @($Script) }
$results = @{}

foreach ($s in $scripts) {
    $results[$s] = Run-Benchmark -Name $s
}

# --- Generate summary.md ---
if (-not $NoSave) {
    $passed  = ($results.Values | Where-Object { $_ -eq 0 }).Count
    $failed  = ($results.Values | Where-Object { $_ -ne 0 }).Count
    $total   = $results.Count

    $summaryPath = "$resultsDir\summary.md"
    $summaryContent = @"
# Benchmark Results - commit $commit

**Timestamp:** $timestamp
**Base URL:** $BaseUrl
**k6 version:** $(k6 version 2>&1 | Select-String "k6 v" | ForEach-Object { $_.Line })

## Results

| Script | Status | Notes |
|--------|--------|-------|
$(foreach ($s in $scripts) {
    $status = if ($results[$s] -eq 0) { "[OK] PASSED" } else { "[WARN] THRESHOLD BREACH" }
    "| ``$s`` | $status | See $s.json |"
})

**$passed/$total scripts passed all thresholds.**
$(if ($failed -gt 0) { "`n> [WARN] $failed script(s) breached thresholds - review .json files for the degradation point. This is expected in stress scenarios." })

## How to reproduce

\`\`\`powershell
# Start backend first:
cd backend
uvicorn app.main:app --port 8000

# Then run benchmarks:
.\benchmarks\run.ps1 -BaseUrl http://localhost:8000
\`\`\`

## Notes on data

- Results labeled ``load_test_reproduced`` are not real production traffic.
- Results labeled ``baseline_real`` (when available) are from production monitoring.
- Stress scenarios are intentionally designed to breach thresholds - the goal is to find the degradation point, not to always pass.
- Run each script 2-3 times and compare: if p99 varies >30%, the environment is noisy (Koyeb is not deterministic).
"@

    Set-Content -Path $summaryPath -Value $summaryContent -Encoding UTF8
    Write-Host ""
    Write-Host "Summary written: $summaryPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "  Passed : $($results.Values | Where-Object { $_ -eq 0 } | Measure-Object | Select-Object -ExpandProperty Count)/$($results.Count)"
Write-Host "  Results: $resultsDir"
Write-Host ""
