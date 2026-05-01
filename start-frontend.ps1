# Starts the Vite dev server. Run from the repo root.
Set-Location "$PSScriptRoot\frontend"

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing npm packages..." -ForegroundColor Cyan
    npm install
}

Write-Host "Starting Vite on http://localhost:5173" -ForegroundColor Green
npm run dev
