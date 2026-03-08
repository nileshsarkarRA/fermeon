"""
Fermeon — LLM Router
Model selection and routing utilities.
"""

from config.models import SUPPORTED_MODELS, DEFAULT_FALLBACK_CHAIN, DEFAULT_MODEL
from typing import Optional
import os


def get_best_available_model(preferred: Optional[str] = None) -> str:
    """
    Return the best model we can actually use given current env vars.
    Checks for API keys before recommending a cloud model.
    Falls back to Ollama if no keys configured.
    """
    if preferred and preferred in SUPPORTED_MODELS:
        return preferred

    # Try fallback chain — use first one with a key available
    for model_id in DEFAULT_FALLBACK_CHAIN:
        config = SUPPORTED_MODELS[model_id]
        if config["type"] == "local":
            return model_id  # Always available (if Ollama is running)
        env_key = config.get("env_key")
        if env_key and os.getenv(env_key):
            return model_id

    return DEFAULT_MODEL


def is_model_available(model_id: str, user_api_key: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if a model can be used.
    Returns (is_available, reason_if_not)
    """
    if model_id not in SUPPORTED_MODELS:
        return False, f"Unknown model '{model_id}'"

    config = SUPPORTED_MODELS[model_id]

    if config["type"] == "local":
        # Would need to actually ping Ollama, but for routing just assume available
        return True, None

    # Check API key
    env_key = config.get("env_key")
    has_env_key = bool(env_key and os.getenv(env_key))
    has_user_key = bool(user_api_key and len(user_api_key) > 10)

    if has_env_key or has_user_key:
        return True, None

    return False, f"No API key for {config['provider']}. Set {env_key} or provide one in Settings."
