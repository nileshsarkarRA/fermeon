@echo off
chcp 65001 >nul

echo.
echo  ============================================================
echo                       F E R M E O N
echo               AI Multi-LLM CAD Generator v1.0
echo  ============================================================
echo.
echo  FIRST TIME SETUP?
echo  -----------------
echo    1. This script handles everything automatically.
echo    2. For LOCAL (free) models: install Ollama from https://ollama.ai/download
echo       then run:  ollama pull qwen2.5:7b
echo    3. For CLOUD models (Gemini, Claude, GPT, etc):
echo       open http://localhost:3000/settings and add your API keys.
echo    4. Your API keys are stored ONLY in your browser - never on any server.
echo.
echo  REQUIREMENTS: Python 3.8+, Node.js 18+
echo  ============================================================
echo.
timeout /t 2 /nobreak >nul

REM ── Check Python ──────────────────────────────────────────────────
py -3.12 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.12 not found.
    echo         Install Python 3.12 from https://python.org
    pause & exit /b 1
)
set PYTHON=py -3.12



REM ── Ollama: smart check - start only if not already running ───────
ollama --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [0/4] Checking Ollama status...
    curl -s --max-time 2 http://localhost:11434/api/version >nul 2>&1
    if %errorlevel% equ 0 (
        echo       Ollama already running.
    ) else (
        echo       Starting Ollama in background...
        start "" /B ollama serve >nul 2>&1
        timeout /t 2 /nobreak >nul
        echo       Ollama started.
    )
) else (
    echo [INFO] Ollama not installed. Local models unavailable.
    echo        Install from https://ollama.ai/download for free local inference.
)

REM ── Install backend dependencies ──────────────────────────────────
echo [1/4] Checking backend dependencies...
cd backend
%PYTHON% -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] Backend pip install failed.
    pause & exit /b 1
)
cd ..

REM ── Create outputs directory ──────────────────────────────────────
if not exist "backend\outputs" mkdir "backend\outputs"

REM ── Install frontend dependencies ─────────────────────────────────


REM ── Start backend ─────────────────────────────────────────────────
echo [2/3] Starting backend on http://localhost:8000 ...
start "Fermeon" cmd /k "title Fermeon && set PYTHONUNBUFFERED=1 && cd backend && py -3.12 -m uvicorn main:app --reload --port 8000 --host 0.0.0.0"



REM ── Wait for servers ──────────────────────────────────────────────
echo.
echo     Waiting for servers to boot...
timeout /t 6 /nobreak >nul

REM ── Open browser ──────────────────────────────────────────────────
cls
echo.
echo  ============================================================
echo                       F E R M E O N
echo               AI Multi-LLM CAD Generator v1.0
echo  ============================================================
echo.
echo    App:       http://localhost:8000
echo    Backend:   http://localhost:8000
echo    API Docs:  http://localhost:8000/docs
echo.
echo    Logs are in the Fermeon Backend window.
echo.
echo    TIP: For free local models run: ollama pull qwen2.5:7b
echo.
start http://localhost:8000

echo  Press any key to close this launcher...
pause >nul
