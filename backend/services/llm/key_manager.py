"""
Fermeon — API Key Manager
Resolves which key to use for a given model (user-provided > env var > None).
SECURITY: Keys are never logged, never stored in DB, memory-only per request.
"""

import os
from typing import Optional


def get_api_key_for_model(model_config: dict, user_provided_key: Optional[str]) -> Optional[str]:
    """
    Key resolution priority:
    1. User-provided key (from request body — passed over HTTPS, never stored)
    2. Environment variable (server default — useful for hosted deployments)
    3. None (for local/Ollama models — no key needed)
    """
    # Local models need no key
    if model_config.get("type") == "local":
        return None

    # User-provided key takes priority
    if user_provided_key and len(user_provided_key) > 10:
        return user_provided_key

    # Fall back to env var
    env_var = model_config.get("env_key")
    if env_var:
        val = os.getenv(env_var)
        if val:
            return val

    return None
