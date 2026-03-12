#!/usr/bin/env bash
# ┌─────────────────────────────────────────────────────────────────┐
# │              F E R M E O N  —  Mac / Linux Launcher             │
# │         AI Multi-LLM CAD Generator v1.0                         │
# └─────────────────────────────────────────────────────────────────┘
set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo ""
echo "  ============================================================"
echo "                      F E R M E O N"
echo "              AI Multi-LLM CAD Generator v1.0"
echo "  ============================================================"
echo ""
echo "  FIRST TIME SETUP?"
echo "  -----------------"
echo "    1. This script handles everything automatically."
echo "    2. For LOCAL (free) models: install Ollama from https://ollama.ai/download"
echo "       then run:  ollama pull qwen2.5:7b"
echo "    3. For CLOUD models (Gemini, Claude, GPT, etc):"
echo "       open http://localhost:8000 → Settings → add your API keys."
echo "    4. Your API keys are stored ONLY in your browser - never on any server."
echo ""
echo "  REQUIREMENTS: Python 3.8+  |  macOS or Linux"
echo "  ============================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

# ── Check Python ──────────────────────────────────────────────────────────────
find_python() {
    for candidate in python3.12 python3.11 python3.10 python3.9 python3.8 python3 python; do
        if command -v "$candidate" &>/dev/null; then
            version=$("$candidate" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -ge 3 ]; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python)
if [ -z "$PYTHON" ]; then
    echo -e "${RED}[ERROR]${RESET} Python 3.8+ not found."
    echo "        Install Python from https://python.org or via:"
    echo "        brew install python@3.12   # (Homebrew)"
    exit 1
fi

echo -e "${GREEN}[✓]${RESET} Python found: $($PYTHON --version 2>&1)  ($PYTHON)"

# ── Ollama: check and start if available ─────────────────────────────────────
if command -v ollama &>/dev/null; then
    if curl -s --max-time 2 http://localhost:11434/api/version &>/dev/null; then
        echo -e "${GREEN}[✓]${RESET} Ollama already running."
    else
        echo -e "${YELLOW}[→]${RESET} Starting Ollama in background..."
        ollama serve &>/dev/null &
        sleep 2
        echo -e "${GREEN}[✓]${RESET} Ollama started."
    fi
else
    echo -e "${YELLOW}[i]${RESET} Ollama not installed — local models unavailable."
    echo "       Install from https://ollama.ai/download for free local inference."
fi

# ── Create outputs directory ──────────────────────────────────────────────────
mkdir -p "$BACKEND_DIR/outputs"

# ── Install backend dependencies ──────────────────────────────────────────────
echo ""
echo "[1/2] Checking backend dependencies..."
$PYTHON -m pip install -r "$BACKEND_DIR/requirements.txt" -q
echo -e "${GREEN}[✓]${RESET} Dependencies OK"

# ── Start backend ─────────────────────────────────────────────────────────────
echo ""
echo "[2/2] Starting Fermeon backend on http://localhost:8000 ..."
echo "      (Press Ctrl+C to stop)"
echo ""
echo "  ============================================================"
echo "    App:       http://localhost:8000"
echo "    API Docs:  http://localhost:8000/docs"
echo "  ============================================================"
echo ""

# Open browser after a short delay (background)
(sleep 3 && open "http://localhost:8000" 2>/dev/null || xdg-open "http://localhost:8000" 2>/dev/null || true) &

# Run uvicorn in foreground (Ctrl+C to stop)
cd "$BACKEND_DIR"
PYTHONUNBUFFERED=1 $PYTHON -m uvicorn main:app --reload --port 8000 --host 0.0.0.0
