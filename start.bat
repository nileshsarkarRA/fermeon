@echo off
chcp 65001 >nul
echo.
echo  ===============================================================
echo                          F E R M E O N                          
echo                   AI Multi-LLM CAD Generator                    
echo  ===============================================================
echo.


REM ── Check Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    pause & exit /b 1
)

REM ── Check Node ────────────────────────────────────────────────────────────
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install from nodejs.org
    pause & exit /b 1
)

REM ── Check Ollama ──────────────────────────────────────────────────────────
ollama --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [0/4] Auto-starting Ollama background engine...
    start "" /B ollama serve >nul 2>&1
) else (
    echo [WARNING] Ollama not found. Local inference will not work.
)

REM ── Install backend dependencies ──────────────────────────────────────────
echo [1/4] Checking backend dependencies...
cd backend
python -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] Backend pip install failed
    pause & exit /b 1
)
cd ..

REM ── Create outputs directory ──────────────────────────────────────────────
if not exist "backend\outputs" mkdir "backend\outputs"

REM ── Install frontend dependencies ─────────────────────────────────────────
echo [2/4] Checking frontend dependencies...
cd frontend
call npm install --silent
if %errorlevel% neq 0 (
    echo [ERROR] npm install failed
    pause & exit /b 1
)
cd ..
echo     Done.

REM ── Start backend ─────────────────────────────────────────────────────────
echo [3/4] Starting Fermeon backend on http://localhost:8000 ...
start "Fermeon Backend" cmd /k "title Fermeon Backend && cd backend && python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0"

REM ── Start frontend ────────────────────────────────────────────────────────
echo [4/4] Starting Fermeon frontend on http://localhost:3000 ...
start "Fermeon Frontend" cmd /k "title Fermeon Frontend && cd frontend && npm run dev"

REM ── Wait for servers ──────────────────────────────────────────────────────
echo.
echo Waiting 5 seconds for servers to boot...
timeout /t 5 /nobreak >nul

REM ── Open browser ─────────────────────────────────────────────────────────
cls
echo.
echo  ===============================================================
echo                          F E R M E O N                          
echo                   AI Multi-LLM CAD Generator                    
echo  ===============================================================
echo.
echo  ✓ Fermeon is online!
echo.
echo  Frontend: http://localhost:3000
echo  Backend:  http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo.
start http://localhost:3000/generate

echo  Press any key to close this launcher (servers keep running in their own windows)...
pause >nul

