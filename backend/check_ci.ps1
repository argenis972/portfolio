# Script to locally verify CI (Windows PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "--- Starting Local CI Verification ---" -ForegroundColor Cyan

function Run-Check {
    param (
        [string]$Name,
        [scriptblock]$Command
    )
    Write-Host "`n$Name..." -ForegroundColor Yellow
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ $Name failed! (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
        return $false
    }
    Write-Host "✅ $Name passed!" -ForegroundColor Green
    return $true
}

$AllPassed = $true

# 1. Verify dependencies
if (!(Run-Check "Verify dependencies" { py -3.12 -m pip install -r requirements.txt -r requirements-dev.txt -q })) { $AllPassed = $false }

# 2. Ruff Check (Linting)
if (!(Run-Check "Ruff Check (Linting)" { py -3.12 -m ruff check . })) { $AllPassed = $false }

# 3. Ruff Format Check (Style)
if (!(Run-Check "Ruff Format Check" { py -3.12 -m ruff format --check . })) {
    Write-Host "HINT: Use 'py -3.12 -m ruff format .' to fix automatically." -ForegroundColor Gray
    $AllPassed = $false
}

# 4. Mypy (Typing)
if (!(Run-Check "Mypy (Typing)" { py -3.12 -m mypy app/core app/use_cases app/controllers app/adapters --ignore-missing-imports --explicit-package-bases })) { $AllPassed = $false }

# 5. Pytest (Tests)
if (!(Run-Check "Pytest (Tests)" { py -3.12 -m pytest })) { $AllPassed = $false }

Write-Host "`n--- Verification complete ---" -ForegroundColor Cyan

if ($AllPassed) {
    Write-Host "✨ ALL PASSED! You can push changes safely." -ForegroundColor Green
} else {
    Write-Host "⚠️  Some checks failed. Fix before pushing." -ForegroundColor Red
    exit 1
}
