"""
Fermeon — Model Registry
All supported LLM models with metadata.
Add a new model here — no other code changes needed.
"""

SUPPORTED_MODELS = {
    # ── LOCAL (Ollama) ───────────────────────────────────────────
    "ollama/codellama:7b": {
        "display_name": "CodeLlama 7B (Local)",
        "provider": "ollama",
        "type": "local",
        "context_window": 16000,
        "cost_per_1k_tokens": 0.0,
        "recommended_for": ["simple parts", "learning"],
        "requires_api_key": False,
        "notes": "Good for simple CadQuery. Needs Ollama running locally.",
    },
    "ollama/codellama:13b": {
        "display_name": "CodeLlama 13B (Local)",
        "provider": "ollama",
        "type": "local",
        "context_window": 16000,
        "cost_per_1k_tokens": 0.0,
        "recommended_for": ["medium complexity"],
        "requires_api_key": False,
        "notes": "More capable than 7B, still free.",
    },
    "ollama/deepseek-coder:6.7b": {
        "display_name": "DeepSeek Coder 6.7B (Local)",
        "provider": "ollama",
        "type": "local",
        "context_window": 16000,
        "cost_per_1k_tokens": 0.0,
        "recommended_for": ["code generation", "fast iteration"],
        "requires_api_key": False,
        "notes": "Fast and decent quality for code.",
    },
    "ollama/qwen2.5:7b": {
        "display_name": "Qwen2.5 7B (Local)",
        "provider": "ollama",
        "type": "local",
        "context_window": 32000,
        "cost_per_1k_tokens": 0.0,
        "recommended_for": ["complex parts", "best local option"],
        "requires_api_key": False,
        "notes": "Fastest local model for CadQuery generation.",
    },

    # ── GOOGLE GEMINI ────────────────────────────────────────────
    "gemini/gemini-2.0-flash": {
        "display_name": "Gemini 2.0 Flash",
        "provider": "google",
        "type": "api",
        "context_window": 1000000,
        "cost_per_1k_tokens": 0.000075,
        "recommended_for": ["fast", "cheap", "large context"],
        "requires_api_key": True,
        "env_key": "GEMINI_API_KEY",
        "notes": "Best bang-for-buck. Often beats pricier models on simple CAD.",
    },
    "gemini/gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "provider": "google",
        "type": "api",
        "context_window": 1000000,
        "cost_per_1k_tokens": 0.00125,
        "recommended_for": ["complex assemblies", "highest accuracy"],
        "requires_api_key": True,
        "env_key": "GEMINI_API_KEY",
        "notes": "Best Gemini model for complex geometry.",
    },

    # ── ANTHROPIC CLAUDE ─────────────────────────────────────────
    "claude-sonnet-4-5": {
        "display_name": "Claude Sonnet 4.5",
        "provider": "anthropic",
        "type": "api",
        "context_window": 200000,
        "cost_per_1k_tokens": 0.003,
        "recommended_for": ["engineering accuracy", "complex constraints"],
        "requires_api_key": True,
        "env_key": "ANTHROPIC_API_KEY",
        "notes": "Excellent instruction-following for mechanical constraints.",
    },
    "claude-haiku-4-5": {
        "display_name": "Claude Haiku 4.5",
        "provider": "anthropic",
        "type": "api",
        "context_window": 200000,
        "cost_per_1k_tokens": 0.00025,
        "recommended_for": ["fast", "cheap", "simple parts"],
        "requires_api_key": True,
        "env_key": "ANTHROPIC_API_KEY",
        "notes": "Fastest Claude model, great for quick iteration.",
    },

    # ── OPENAI ───────────────────────────────────────────────────
    "gpt-4o": {
        "display_name": "GPT-4o",
        "provider": "openai",
        "type": "api",
        "context_window": 128000,
        "cost_per_1k_tokens": 0.005,
        "recommended_for": ["general purpose", "well-documented CAD"],
        "requires_api_key": True,
        "env_key": "OPENAI_API_KEY",
        "notes": "Popular and well-rounded.",
    },
    "gpt-4o-mini": {
        "display_name": "GPT-4o Mini",
        "provider": "openai",
        "type": "api",
        "context_window": 128000,
        "cost_per_1k_tokens": 0.000150,
        "recommended_for": ["fast", "cheap"],
        "requires_api_key": True,
        "env_key": "OPENAI_API_KEY",
        "notes": "Best cheap OpenAI option.",
    },

    # ── GROQ (Fast inference) ────────────────────────────────────
    "groq/llama-3.1-70b-versatile": {
        "display_name": "Llama 3.1 70B (Groq)",
        "provider": "groq",
        "type": "api",
        "context_window": 128000,
        "cost_per_1k_tokens": 0.00059,
        "recommended_for": ["fast", "open weights", "medium complexity"],
        "requires_api_key": True,
        "env_key": "GROQ_API_KEY",
        "notes": "Groq hardware makes this very fast.",
    },
    "groq/deepseek-r1-distill-llama-70b": {
        "display_name": "DeepSeek R1 70B (Groq)",
        "provider": "groq",
        "type": "api",
        "context_window": 128000,
        "cost_per_1k_tokens": 0.00075,
        "recommended_for": ["reasoning-heavy geometry", "complex math"],
        "requires_api_key": True,
        "env_key": "GROQ_API_KEY",
        "notes": "Reasoning model — shows its work, great for complex constraints.",
    },

    # ── MISTRAL ──────────────────────────────────────────────────
    "mistral/codestral-latest": {
        "display_name": "Codestral (Mistral)",
        "provider": "mistral",
        "type": "api",
        "context_window": 32000,
        "cost_per_1k_tokens": 0.001,
        "recommended_for": ["code generation specialist"],
        "requires_api_key": True,
        "env_key": "MISTRAL_API_KEY",
        "notes": "Trained specifically on code. Solid for CadQuery.",
    },
}

# Default fallback chain: try these in order if a model fails or has no key
DEFAULT_FALLBACK_CHAIN = [
    "gemini/gemini-2.0-flash",
    "groq/llama-3.1-70b-versatile",
    "ollama/qwen2.5:7b",
]

# Default model if none specified
DEFAULT_MODEL = "gemini/gemini-2.0-flash"
