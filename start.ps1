<#
.SYNOPSIS
    Starts the Fermeon AI CAD Generator backend and frontend.
.DESCRIPTION
    Installs dependencies and launches the FastAPI server and Next.js frontend in separate windows.
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
    $null = Get-Command python -ErrorAction Stop
}
catch {
    Write-Error "[ERROR] Python not found. Please install Python 3.11+ from https://python.org"
    Exit 1
}

# ── Setup Backend ───────────────────────────────────────────────────────────
Write-Host "[1/4] Installing backend dependencies..." -ForegroundColor Yellow
Push-Location backend
# Using cmd to pipe output correctly and wait
cmd /c "python -m pip install -r requirements.txt -q"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] Failed to install backend dependencies."
    Exit 1
}
if (!(Test-Path "outputs")) {
    New-Item -ItemType Directory -Force -Path "outputs" | Out-Null
}
Pop-Location
Write-Host "      Done." -ForegroundColor Green



# ── Launch Servers ──────────────────────────────────────────────────────────
Write-Host "[3/4] Starting Fermeon backend on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "title Fermeon Backend && cd backend && python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0"

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
