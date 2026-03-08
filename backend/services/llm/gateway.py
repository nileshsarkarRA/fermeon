"""
Fermeon — LLM Gateway ★ CORE
Single entry point for all LLM calls. Pass any model string, get CadQuery code back.
Uses LiteLLM for unified API across 100+ models.
"""

from __future__ import annotations
import os
import litellm
from typing import Optional
from config.models import SUPPORTED_MODELS, DEFAULT_FALLBACK_CHAIN
from .prompt_formatter import format_prompt_for_model, build_correction_prompt
from .response_parser import extract_code_from_response
from .key_manager import get_api_key_for_model

# Suppress LiteLLM verbose logging
litellm.set_verbose = False

# Tell LiteLLM where Ollama lives (can be overridden per-request)
litellm.api_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class GatewayRequest(BaseModel):
    prompt: str
    model: str
    system_prompt: str
    examples: List[str]
    user_api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4096


class LLMGateway:
    """
    Single entry point for all LLM calls in Fermeon.
    Swap the model string -> same code, any provider.
    """

    async def generate_cad_code(
        self,
        request: GatewayRequest,
    ) -> dict:
        """
        Core generation method. Works with any supported model.
        Returns: {success, code, raw_response, model_used, usage}
        """
        if model not in SUPPORTED_MODELS:
            return {
                "success": False,
                "error": f"Unknown model: {model}. Available: {list(SUPPORTED_MODELS.keys())}",
                "model_used": model,
            }

        model_config = SUPPORTED_MODELS[model]
        api_key = get_api_key_for_model(model_config, user_api_key)
        api_base = self._get_api_base(model_config)

        # Format prompt correctly for this model family
        messages = format_prompt_for_model(
            model=model,
            system_prompt=system_prompt,
            user_prompt=prompt,
            examples=examples,
            model_config=model_config,
        )

        try:
            kwargs = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=90,
            )
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base

            response = await litellm.acompletion(**kwargs)

            raw_text = response.choices[0].message.content

            # Extract the actual Python code block
            code = extract_code_from_response(raw_text)

            return {
                "success": True,
                "code": code,
                "raw_response": raw_text,
                "model_used": model,
                "usage": {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
                    "estimated_cost_usd": self._estimate_cost(model, response.usage),
                },
            }

        except Exception as e:
            error_msg = str(e)
            # Mask API keys in error messages for security
            if api_key and api_key in error_msg:
                error_msg = error_msg.replace(api_key, "[REDACTED]")
            return {
                "success": False,
                "error": error_msg,
                "model_used": model,
            }

    async def generate_with_fallback(
        self,
        prompt: str,
        preferred_model: str,
        system_prompt: str,
        examples: List[str],
        user_api_key: Optional[str] = None,
    ) -> dict:
        """
        Try preferred model first. Fall back through DEFAULT_FALLBACK_CHAIN if it fails.
        The fallback chain skips the preferred model if it's already in the chain.
        """
        models_to_try = [preferred_model] + [
            m for m in DEFAULT_FALLBACK_CHAIN if m != preferred_model
        ]

        last_error = "No models tried"
        for model in models_to_try:
            result = await self.generate_cad_code(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                examples=examples,
                user_api_key=user_api_key,
            )
            if result["success"]:
                result["fallback_used"] = (model != preferred_model)
                result["fallback_model"] = model if model != preferred_model else None
                return result
            last_error = result.get("error", "Unknown error")

        return {
            "success": False,
            "error": f"All models failed. Last error: {last_error}",
            "tried": models_to_try,
            "model_used": preferred_model,
        }

    async def self_correct(
        self,
        original_prompt: str,
        failed_code: str,
        error_message: str,
        model: str,
        system_prompt: str,
        user_api_key: Optional[str] = None,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> dict:
        """
        Feed execution error back to LLM for self-correction.
        The model sees its own broken code + the error and tries to fix it.
        """
        if attempt > max_attempts:
            return {"success": False, "error": "Max correction attempts reached"}

        correction_prompt = build_correction_prompt(
            original_prompt=original_prompt,
            failed_code=failed_code,
            error_message=error_message,
        )

        return await self.generate_cad_code(
            prompt=correction_prompt,
            model=model,
            system_prompt=system_prompt,
            examples=[],  # No examples during correction — save tokens
            user_api_key=user_api_key,
            temperature=0.05,  # Even lower temp for corrections
        )

    def _get_api_base(self, model_config: dict) -> Optional[str]:
        """Return custom API base URL for Ollama, None for cloud providers."""
        if model_config.get("provider") == "ollama":
            return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return None

    def _estimate_cost(self, model: str, usage) -> float:
        """Estimate API cost based on token usage and per-model pricing."""
        config = SUPPORTED_MODELS.get(model, {})
        rate = config.get("cost_per_1k_tokens", 0.0)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        total_tokens = prompt_tokens + completion_tokens
        return round((total_tokens / 1000) * rate, 6)
