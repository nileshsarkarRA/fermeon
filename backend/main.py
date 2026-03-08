"""
Fermeon — FastAPI Application Entry Point
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import generate, models, export, gpu
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create output directory on startup."""
    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Fermeon backend running — output dir: {output_dir.resolve()}")
    print(f"   Default model: {settings.default_model}")
    print(f"   Ollama URL: {settings.ollama_base_url}")
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


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": "Fermeon",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    return {
        "message": "Fermeon API — AI Multi-LLM CAD Generator",
        "docs": "/docs",
        "health": "/health",
        "models": "/api/models",
    }
