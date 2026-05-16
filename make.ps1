param (
    [string]$target = "help"
)

$commands = @{
    "dev"         = "Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd backend; .venv\Scripts\activate; python -m uvicorn app.main:app --host localhost --port 8000 --reload'; cd frontend; npm run dev"
    "dev-back"    = "cd backend; .venv\Scripts\activate; python -m uvicorn app.main:app --host localhost --port 8000 --reload"
    "dev-front"   = "cd frontend; npm run dev"
    "test-back"   = "cd backend; .venv\Scripts\activate; python -m pytest"
    "test-front"  = "cd frontend; npm run test"
    "test"        = "cd backend; .venv\Scripts\activate; python -m pytest; cd ../frontend; npm run test"
    "lint-back"   = "cd backend; .venv\Scripts\activate; ruff check .; mypy ."
    "lint-front"  = "cd frontend; npm run lint; npx tsc --noEmit"
    "format-back" = "cd backend; .venv\Scripts\activate; ruff format ."
    "lint"        = "cd backend; .venv\Scripts\activate; ruff check .; mypy .; cd ../frontend; npm run lint; npx tsc --noEmit"
    "help"        = "Write-Host 'Available shortcuts: dev, dev-back, dev-front, test-back, test-front, test, lint-back, lint-front, format-back, lint' -ForegroundColor Yellow"
}

if ($commands.ContainsKey($target)) {
    Write-Host "🚀 Running shortcut: $target" -ForegroundColor Cyan
    Invoke-Expression $commands[$target]
}
else {
    Write-Host "❌ Shortcut '$target' not found." -ForegroundColor Red
    Invoke-Expression $commands["help"]
}
