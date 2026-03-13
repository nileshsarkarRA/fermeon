"""
Fermeon — LLM Gateway ★ CORE
Single entry point for all LLM calls. Pass any model string, get CadQuery code back.
Uses LiteLLM for unified API across 100+ models.

v2 improvements:
- Structured spec pipeline: enhance_prompt_text → spec JSON → spec-to-code generation
- self_correct() receives enhanced_spec for better context
- All cloud models get ultra-strict output enforcement via prompt_formatter
"""

from __future__ import annotations
import os
import re
import litellm
from typing import Optional, List
from pydantic import BaseModel
from config.models import SUPPORTED_MODELS, DEFAULT_FALLBACK_CHAIN
from .prompt_formatter import (
    format_prompt_for_model,
    format_spec_prompt_for_model,
    build_correction_prompt,
)
from .response_parser import extract_code_from_response, extract_spec_json
from .key_manager import get_api_key_for_model

# Suppress LiteLLM verbose logging
litellm.set_verbose = False


class GatewayRequest(BaseModel):
    prompt: str
    model: str
    system_prompt: str
    examples: List[str]
    user_api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 8192


class LLMGateway:
    """
    Single entry point for all LLM calls in Fermeon.
    Swap the model string -> same code, any provider.
    """

    async def generate_cad_code(
        self,
        prompt: str,
        model: str,
        system_prompt: str,
        examples: List[str],
        user_api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 8192,
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
                timeout=120,
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

    async def generate_from_spec(
        self,
        spec_json: dict,
        model: str,
        system_prompt: str,
        user_api_key: Optional[str] = None,
    ) -> dict:
        """
        Generate CadQuery code from a structured JSON geometry spec.
        Higher reliability than freeform prompt since the LLM receives
        explicit dimensions, components and assembly order — no interpretation needed.
        Returns: {success, code, raw_response, model_used, usage}
        """
        if model not in SUPPORTED_MODELS:
            return {
                "success": False,
                "error": f"Unknown model: {model}",
                "model_used": model,
            }

        model_config = SUPPORTED_MODELS[model]
        api_key = get_api_key_for_model(model_config, user_api_key)
        api_base = self._get_api_base(model_config)

        messages = format_spec_prompt_for_model(
            model=model,
            system_prompt=system_prompt,
            spec_json=spec_json,
            model_config=model_config,
        )

        try:
            kwargs = dict(
                model=model,
                messages=messages,
                temperature=0.05,   # very low — we want exact spec implementation
                max_tokens=8192,
                timeout=120,
            )
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base

            response = await litellm.acompletion(**kwargs)
            raw_text = response.choices[0].message.content
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
        spec_json: Optional[dict] = None,
    ) -> dict:
        """
        Try preferred model first. Fall back through DEFAULT_FALLBACK_CHAIN if it fails.
        If spec_json is provided, uses the spec-to-code path (higher reliability).
        The fallback chain skips the preferred model if it's already in the chain.
        """
        models_to_try = [preferred_model] + [
            m for m in DEFAULT_FALLBACK_CHAIN if m != preferred_model
        ]

        last_error = "No models tried"
        for model in models_to_try:
            if spec_json:
                # Spec path: higher reliability
                result = await self.generate_from_spec(
                    spec_json=spec_json,
                    model=model,
                    system_prompt=system_prompt,
                    user_api_key=user_api_key,
                )
            else:
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
        max_attempts: int = 5,
        domain: str = "mechanical",
        enhanced_spec: Optional[dict] = None,
    ) -> dict:
        """
        Feed execution error back to LLM for self-correction.
        The model sees its own broken code + the error + a targeted hint.
        enhanced_spec (if available) is included so the model knows what it should build.
        """
        if attempt > max_attempts:
            return {"success": False, "error": "Max correction attempts reached"}

        correction_prompt = build_correction_prompt(
            original_prompt=original_prompt,
            failed_code=failed_code,
            error_message=error_message,
            domain=domain,
            enhanced_spec=enhanced_spec,
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

    async def enhance_prompt_text(
        self,
        prompt: str,
        model: str,
        user_api_key: Optional[str] = None,
    ) -> dict:
        """
        Trip 1: Enhance the user prompt using the Leap 71 enhancer template.
        Adds geometric precision, domain classification, and engineering parameters.
        Returns a structured JSON spec (SPEC_JSON key) in addition to the prose spec.

        Soft-fails: returns the original prompt if the LLM call fails.
        Returns: {success, enhanced_prompt, spec_json, detected_domain, model_used, usage}
        """
        if model not in SUPPORTED_MODELS:
            return {"success": True, "enhanced_prompt": prompt, "spec_json": None, "detected_domain": None, "model_used": model, "usage": {}}

        model_config = SUPPORTED_MODELS[model]
        api_key = get_api_key_for_model(model_config, user_api_key)
        api_base = self._get_api_base(model_config)

        from pathlib import Path
        enhancer_path = Path(__file__).parent.parent.parent / "prompts" / "enhancer_prompt.txt"
        try:
            enhancer_system = enhancer_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {"success": True, "enhanced_prompt": prompt, "spec_json": None, "detected_domain": None, "model_used": model, "usage": {}}

        from .prompt_formatter import format_prompt_for_model as _fmt
        messages = _fmt(
            model=model,
            system_prompt=enhancer_system,
            user_prompt=prompt,
            examples=[],
            model_config=model_config,
        )
        # Override the output rule for the enhancer — it outputs prose, not code
        # We do this by replacing the last user message
        if messages and messages[-1]["role"] == "user":
            content = messages[-1]["content"]
            # Remove the code output rule (enhancer produces text, not code)
            content = re.sub(r'⛔ OUTPUT RULE.*', '', content, flags=re.DOTALL).strip()
            messages[-1]["content"] = content

        try:
            kwargs: dict = dict(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
                timeout=90,
            )
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base

            response = await litellm.acompletion(**kwargs)
            enhanced = response.choices[0].message.content.strip()

            # Parse the DOMAIN: line from enhancer output
            detected_domain = None
            domain_match = re.search(r'^DOMAIN:\s*(\w+)', enhanced, re.MULTILINE | re.IGNORECASE)
            if domain_match:
                detected_domain = domain_match.group(1).strip().lower()

            # Extract structured spec JSON if present
            spec_json = extract_spec_json(enhanced)

            return {
                "success": True,
                "enhanced_prompt": enhanced or prompt,
                "spec_json": spec_json,
                "detected_domain": detected_domain,
                "model_used": model,
                "usage": {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
                    "estimated_cost_usd": self._estimate_cost(model, response.usage),
                },
            }

        except Exception as e:
            error_msg = str(e)
            if api_key and api_key in error_msg:
                error_msg = error_msg.replace(api_key, "[REDACTED]")
            # Soft-fail: return original prompt so the pipeline can continue
            return {
                "success": False,
                "error": error_msg,
                "enhanced_prompt": prompt,
                "spec_json": None,
                "detected_domain": None,
                "model_used": model,
                "usage": {},
            }

    async def generate_cem_params(
        self,
        prompt: str,
        model: str,
        schema_json: str,
        cem_name: str,
        user_api_key: Optional[str] = None,
    ) -> dict:
        """
        Leap 71 / Noyron approach: ask LLM to extract CEM parameters as JSON.
        The LLM only outputs numbers and strings — CadQuery syntax errors are impossible.
        Returns: {success, params: dict, raw_response, model_used, usage?}
        """
        if model not in SUPPORTED_MODELS:
            return {"success": False, "error": f"Unknown model: {model}", "model_used": model}

        model_config = SUPPORTED_MODELS[model]
        api_key = get_api_key_for_model(model_config, user_api_key)
        api_base = self._get_api_base(model_config)

        from .prompt_formatter import format_cem_prompt_for_model
        messages = format_cem_prompt_for_model(
            model=model,
            cem_name=cem_name,
            schema_json=schema_json,
            user_prompt=prompt,
            model_config=model_config,
        )

        try:
            kwargs: dict = dict(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=512,
                timeout=60,
            )
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base

            response = await litellm.acompletion(**kwargs)
            raw_text = response.choices[0].message.content

            from .response_parser import extract_json_params
            params = extract_json_params(raw_text)

            if params is None:
                return {
                    "success": False,
                    "error": f"LLM did not return valid JSON. Response: {raw_text[:300]!r}",
                    "model_used": model,
                    "raw_response": raw_text,
                }

            return {
                "success": True,
                "params": params,
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
            if api_key and api_key in error_msg:
                error_msg = error_msg.replace(api_key, "[REDACTED]")
            return {"success": False, "error": error_msg, "model_used": model}
