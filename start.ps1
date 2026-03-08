<#
.SYNOPSIS
    Starts the Fermeon AI CAD Generator.
.DESCRIPTION
    Installs backend dependencies and launches the FastAPI server.
    The frontend is static HTML/JS served directly by FastAPI — no Node.js required.
#>

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "  ===============================================================" -ForegroundColor Cyan
Write-Host "                          F E R M E O N                          " -ForegroundColor Cyan
Write-Host "                   AI Multi-LLM CAD Generator                    " -ForegroundColor Cyan
Write-Host "  ===============================================================" -ForegroundColor Cyan
Write-Host ""




try {
    $null = py -3.12 --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
}
catch {
    Write-Error "[ERROR] Python 3.12 not found. Please install it from https://python.org"
    Exit 1
}

# ── Setup Backend ───────────────────────────────────────────────────────────
Write-Host "[1/2] Installing backend dependencies..." -ForegroundColor Yellow
Push-Location backend
py -3.12 -m pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] Failed to install backend dependencies."
    Exit 1
}
if (!(Test-Path "outputs")) {
    New-Item -ItemType Directory -Force -Path "outputs" | Out-Null
}
Pop-Location
Write-Host "      Done." -ForegroundColor Green



# ── Launch Backend ──────────────────────────────────────────────────────────────────
Write-Host "[2/2] Starting Fermeon on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "title Fermeon && set PYTHONUNBUFFERED=1 && cd backend && py -3.12 -m uvicorn main:app --reload --port 8000 --host 0.0.0.0"

Start-Sleep -Seconds 3



# ── Open Browser ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ✓ Fermeon is starting up!" -ForegroundColor Green
Write-Host ""
Write-Host "  App:      http://localhost:8000"
Write-Host "  Backend:  http://localhost:8000"
Write-Host "  API Docs: http://localhost:8000/docs"
Write-Host ""
Write-Host "  Opening browser..." -ForegroundColor Yellow
Start-Process "http://localhost:8000/"

Write-Host ""
Write-Host "  Press any key to exit this launcher (servers keep running in their own windows)..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
