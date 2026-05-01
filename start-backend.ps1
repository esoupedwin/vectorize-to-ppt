# Starts the FastAPI backend. Run from the repo root.
Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet

Write-Host "Starting FastAPI on http://localhost:8000" -ForegroundColor Green
uvicorn main:app --reload --host 0.0.0.0 --port 8000
