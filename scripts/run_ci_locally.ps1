# Reproduce the CI lint + test workflow locally.
# Run from repo root:  .\scripts\run_ci_locally.ps1
# Exit code is 0 only when all steps pass.

$ErrorActionPreference = "Stop"

function Check-Exit {
    if ($LASTEXITCODE -ne 0) { throw "Step failed with exit code $LASTEXITCODE" }
}

Write-Host "=== 1. uv sync (frozen) ===" -ForegroundColor Cyan
uv sync --frozen
Check-Exit

Write-Host "`n=== 2. ruff check ===" -ForegroundColor Cyan
uv run ruff check src/ tests/
Check-Exit

Write-Host "`n=== 3. pytest ===" -ForegroundColor Cyan
uv run pytest tests/ -v --tb=short -q
Check-Exit

Write-Host "`n=== All CI checks passed ===" -ForegroundColor Green
