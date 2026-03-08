"""
Fermeon — Models Router
GET /models — lists all supported models with live Ollama availability check.
"""

from __future__ import annotations
import subprocess
from fastapi import APIRouter
from config.models import SUPPORTED_MODELS, DEFAULT_FALLBACK_CHAIN

router = APIRouter()


@router.get("/models")
async def list_models():
    """
    Returns all supported models with availability status.
    - Cloud models: available if an API key env var is set (or user provides one)
    - Local/Ollama models: checks if Ollama is running and model is pulled
    """
    models = []
    ollama_pulled = _get_available_ollama_models()
    ollama_running = ollama_pulled is not None  # None means Ollama didn't respond

    for model_id, config in SUPPORTED_MODELS.items():
        available = True
        availability_note = None

        if config["type"] == "local":
            if not ollama_running:
                available = False
                availability_note = "Ollama is not running. Start with: ollama serve"
            else:
                model_name = model_id.replace("ollama/", "")
                available = any(
                    model_name in pulled_model for pulled_model in (ollama_pulled or [])
                )
                if not available:
                    availability_note = f"Run: ollama pull {model_name}"
        # Cloud models: always show as potentially available (user provides key in Settings)

        models.append({
            "id": model_id,
            "display_name": config["display_name"],
            "provider": config["provider"],
            "type": config["type"],
            "context_window": config["context_window"],
            "cost_per_1k_tokens": config["cost_per_1k_tokens"],
            "recommended_for": config["recommended_for"],
            "requires_api_key": config["requires_api_key"],
            "env_key": config.get("env_key"),
            "notes": config.get("notes", ""),
            "available": available,
            "availability_note": availability_note,
            "is_default_fallback": model_id in DEFAULT_FALLBACK_CHAIN,
        })

    return {
        "models": models,
        "ollama_running": ollama_running,
        "default_fallback_chain": DEFAULT_FALLBACK_CHAIN,
    }


def _get_available_ollama_models() -> list:
    """
    Check which Ollama models are pulled and ready.
    Returns None if Ollama is not running.
    Returns empty list if running but no models pulled.
    """
    try:
        # Use shell=True on Windows to ensure 'ollama' command is found if not in direct PATH executable 
        result = subprocess.run(
            "ollama list",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        # Parse model names from tabular output (skip header line)
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:
            return []
            
        models = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except FileNotFoundError:
        return None  # ollama CLI not installed
    except Exception:
        return None
