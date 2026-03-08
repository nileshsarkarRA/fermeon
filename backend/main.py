"""
Fermeon — FastAPI Application Entry Point
"""

import os
import subprocess
import time
import logging

# Suppress annoying LiteLLM startup/debug messages globally before imports
os.environ["LITELLM_LOG"] = "ERROR"
os.environ["SUPPRESS_LITELLM_LOGS"] = "True"
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import generate, models, export, gpu, logs
from config.settings import settings


def _ensure_ollama_running() -> None:
    """
    Check if Ollama is already serving; if not, start it in the background.
    Won't do anything if Ollama CLI is not installed.
    """
    try:
        # Quick health check — Ollama exposes /api/version
        import urllib.request
        req = urllib.request.Request(
            "http://localhost:11434/api/version",
            headers={"User-Agent": "fermeon-health"},
        )
        urllib.request.urlopen(req, timeout=2)
        print("   Ollama already running ✔")
        return
    except Exception:
        pass  # Not running yet — try to start it

    # Try to start ollama serve
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        time.sleep(2)  # Give it a moment to boot
        print("   Ollama started automatically ✔")
    except FileNotFoundError:
        print("   Ollama not installed — local inference unavailable")
    except Exception as e:
        print(f"   Could not start Ollama: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create output directory and ensure Ollama is running on startup."""
    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Fermeon backend running — output dir: {output_dir.resolve()}")
    print(f"   Default model: {settings.default_model}")
    print(f"   Ollama URL: {settings.ollama_base_url}")
    _ensure_ollama_running()
    yield


app = FastAPI(
    title="Fermeon API",
    description="AI-powered multi-LLM CAD generator — turns natural language into STEP/STL files",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server and production domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        settings.frontend_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(generate.router, prefix="/api", tags=["Generate"])
app.include_router(models.router, prefix="/api", tags=["Models"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(gpu.router, prefix="/api", tags=["GPU"])
app.include_router(logs.router, prefix="/api", tags=["Logs"])

# Mount endpoints for static files
# 1. Output CAD files (STL, STEP)
app.mount("/files", StaticFiles(directory=settings.output_dir), name="files")

# 2. Brand assets (logos, favicon)
assets_dir = Path(__file__).parent.parent / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# 3. Serve the simple HTML frontend at root (MUST be last — catches all unmatched paths)
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": "Fermeon",
        "version": "1.0.0",
    }
