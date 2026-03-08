# 🏗️ AI CAD GENERATOR — MULTI-LLM BUILD GUIDE
> Works with ANY LLM: Ollama (local) · Claude · Gemini · OpenAI · Mistral · Groq · Cohere
> One prompt format → any model → accurate CadQuery code → real STEP/STL files

---

## 0. THE BIG IDEA: LLM-AGNOSTIC ARCHITECTURE

Instead of being locked to one AI provider, this system uses a **unified LLM gateway layer**.
You write prompt logic once. Any model plugs in. Users can even pick their own.

```
User Prompt
    │
    ▼
┌─────────────────────────────┐
│    LLM ROUTER / GATEWAY     │  ← picks model based on user choice / fallback rules
└─────────────┬───────────────┘
              │
    ┌─────────┴──────────┐
    │   ADAPTER LAYER    │  ← normalizes all APIs to one interface
    └─────────┬──────────┘
              │
    ┌─────────▼──────────────────────────────────────────────┐
    │  Ollama  │  Claude  │  Gemini  │  OpenAI  │  Groq  │ …│
    └────────────────────────────────────────────────────────┘
              │
    ┌─────────▼──────────┐
    │   CadQuery Code    │  ← same output format regardless of model
    └─────────┬──────────┘
              │
    ┌─────────▼──────────┐
    │  Execute + Export  │  ← STEP / STL / OBJ
    └────────────────────┘
```

**Why this matters:**
- Users can run it **100% locally** with Ollama (no API keys, no costs, no data leaving machine)
- Paid APIs (Gemini Flash = cheap, Claude = accurate, GPT-4o = popular) are drop-in
- You can benchmark models against each other for CAD accuracy
- No vendor lock-in ever

---

## 1. TECH STACK

| Layer | Choice | Why |
|---|---|---|
| Frontend | Vanilla HTML/JS | No-build, lightweight, blazing fast |
| Backend | FastAPI (Python) | Python-native CAD libs |
| LLM Gateway | **LiteLLM** | Unified API for 100+ models |
| Local LLMs | **Ollama** | Run any open model locally |
| CAD Engine | CadQuery | Parametric geometry |
| 3D Viewer | Three.js / @react-three/fiber | Browser 3D |
| Storage | Supabase + S3 | Metadata + files |
| Auth | Local Storage | Fully local user API keys |
| Deployment | Any Static Server (or native via FastAPI) | Simple architecture |

### Why LiteLLM?

LiteLLM is a Python library that gives you **one unified API** for every major LLM provider.
You call `litellm.completion()` with a model string like `"ollama/codellama"` or `"gemini/gemini-1.5-flash"` or `"claude-sonnet-4"` — same code, any model.

```python
# Without LiteLLM — you'd write this 6 times for 6 providers:
import anthropic; client = anthropic.Anthropic(); response = client.messages.create(...)
import google.generativeai as genai; genai.configure(...); model = genai.GenerativeModel(...)
import openai; client = openai.OpenAI(); response = client.chat.completions.create(...)
# ... etc

# With LiteLLM — one call for all of them:
import litellm
response = litellm.completion(model="claude-sonnet-4", messages=[...])
response = litellm.completion(model="gemini/gemini-1.5-flash", messages=[...])
response = litellm.completion(model="ollama/codellama:13b", messages=[...])
response = litellm.completion(model="groq/llama-3.1-70b-versatile", messages=[...])
```

---

## 2. SUPPORTED MODELS + CONFIGURATION

### 2.1 Model Registry

```python
# backend/config/models.py

SUPPORTED_MODELS = {
    # ── LOCAL (Ollama) ──────────────────────────────────────────
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
    },
    "ollama/deepseek-coder:6.7b": {
        "display_name": "DeepSeek Coder 6.7B (Local)",
        "provider": "ollama",
        "type": "local",
        "context_window": 16000,
        "cost_per_1k_tokens": 0.0,
        "recommended_for": ["code generation", "fast iteration"],
        "requires_api_key": False,
    },
    "ollama/qwen2.5-coder:14b": {
        "display_name": "Qwen2.5 Coder 14B (Local)",
        "provider": "ollama",
        "type": "local",
        "context_window": 32000,
        "cost_per_1k_tokens": 0.0,
        "recommended_for": ["complex parts", "best local option"],
        "requires_api_key": False,
    },

    # ── GOOGLE GEMINI ────────────────────────────────────────────
    "gemini/gemini-2.0-flash": {
        "display_name": "Gemini 2.0 Flash",
        "provider": "google",
        "type": "api",
        "context_window": 1000000,
        "cost_per_1k_tokens": 0.000075,  # ~$0.075 per 1M tokens
        "recommended_for": ["fast", "cheap", "large context"],
        "requires_api_key": True,
        "env_key": "GEMINI_API_KEY",
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
    },

    # ── ANTHROPIC CLAUDE ─────────────────────────────────────────
    "claude-sonnet-4": {
        "display_name": "Claude Sonnet 4",
        "provider": "anthropic",
        "type": "api",
        "context_window": 200000,
        "cost_per_1k_tokens": 0.003,
        "recommended_for": ["engineering accuracy", "complex constraints"],
        "requires_api_key": True,
        "env_key": "ANTHROPIC_API_KEY",
    },
    "claude-haiku-4-5": {
        "display_name": "Claude Haiku",
        "provider": "anthropic",
        "type": "api",
        "context_window": 200000,
        "cost_per_1k_tokens": 0.00025,
        "recommended_for": ["fast", "cheap", "simple parts"],
        "requires_api_key": True,
        "env_key": "ANTHROPIC_API_KEY",
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
    },
}

# Default fallback chain: try these in order if a model fails
DEFAULT_FALLBACK_CHAIN = [
    "gemini/gemini-2.0-flash",
    "groq/llama-3.1-70b-versatile",
    "ollama/qwen2.5-coder:14b",
]
```

---

## 3. DIRECTORY STRUCTURE

```
ai-cad-generator/
│
├── frontend/
│   ├── index.html                 # Main generator UI
│   ├── styles.css                 # Sleek UI styling
│   └── app.js                     # Logic and API calls
│
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   │
│   ├── routers/
│   │   ├── generate.py               # POST /generate
│   │   ├── models.py                 # GET /models (list available)
│   │   ├── execute.py
│   │   └── export.py
│   │
│   ├── services/
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── gateway.py            # ★ CORE: LiteLLM unified caller
│   │   │   ├── router.py             # Model selection logic
│   │   │   ├── prompt_formatter.py   # Format prompts per model quirks
│   │   │   ├── response_parser.py    # Extract code from any response format
│   │   │   └── key_manager.py        # Handle user-provided API keys
│   │   │
│   │   ├── cad_executor.py
│   │   ├── mesh_service.py
│   │   └── storage_service.py
│   │
│   ├── config/
│   │   ├── models.py                 # SUPPORTED_MODELS registry (above)
│   │   └── settings.py               # App settings via pydantic-settings
│   │
│   ├── prompts/
│   │   ├── system_prompt.txt         # Base system prompt (model-agnostic)
│   │   ├── model_overrides/
│   │   │   ├── ollama.txt            # Adjustments for local models
│   │   │   ├── gemini.txt            # Gemini-specific tweaks
│   │   │   └── reasoning_models.txt  # For R1, o1 — no system prompt tricks
│   │   ├── examples/
│   │   │   ├── bracket.py
│   │   │   ├── nozzle.py
│   │   │   ├── gear.py
│   │   │   ├── heat_exchanger.py
│   │   │   └── enclosure.py
│   │   └── domain_prompts/
│   │       ├── aerospace.txt
│   │       ├── mechanical.txt
│   │       ├── architecture.txt
│   │       └── biomedical.txt
│   │
│   ├── sandbox/
│   │   ├── executor.py
│   │   └── allowed_imports.py
│   │
│   └── tests/
│       ├── test_llm_gateway.py
│       ├── test_executor.py
│       └── benchmarks/
│           ├── run_benchmark.py      # Test all models on same prompts
│           └── results/              # JSON results per model
│
└── docker/
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    ├── docker-compose.yml
    └── docker-compose.ollama.yml     # Includes Ollama service
```

---

## 4. THE LLM GATEWAY (Most Important File)

This is the heart of the multi-LLM system. Everything routes through here.

```python
# backend/services/llm/gateway.py

import litellm
import os
import json
from typing import Optional, AsyncGenerator
from ..config.models import SUPPORTED_MODELS, DEFAULT_FALLBACK_CHAIN
from .prompt_formatter import format_prompt_for_model
from .response_parser import extract_code_from_response
from .key_manager import get_api_key_for_model

# Tell LiteLLM where Ollama lives
litellm.api_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

class LLMGateway:
    """
    Single entry point for all LLM calls.
    Pass any model string. Get CadQuery code back.
    """

    async def generate_cad_code(
        self,
        prompt: str,
        model: str,
        system_prompt: str,
        examples: list[str],
        user_api_key: Optional[str] = None,
        stream: bool = False,
    ) -> dict:
        """
        Core generation method. Works with any supported model.
        """
        # 1. Validate model is known
        if model not in SUPPORTED_MODELS:
            raise ValueError(f"Unknown model: {model}. Available: {list(SUPPORTED_MODELS.keys())}")

        model_config = SUPPORTED_MODELS[model]

        # 2. Get API key (user-provided > env var > None for local)
        api_key = self._resolve_api_key(model_config, user_api_key)

        # 3. Format prompt for this specific model's quirks
        messages = format_prompt_for_model(
            model=model,
            system_prompt=system_prompt,
            user_prompt=prompt,
            examples=examples,
            model_config=model_config,
        )

        # 4. Call the model via LiteLLM
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                api_key=api_key,
                api_base=self._get_api_base(model_config),
                temperature=0.1,         # Low temp for code accuracy
                max_tokens=4096,
                timeout=60,
            )

            raw_text = response.choices[0].message.content

            # 5. Extract Python code block from response
            code = extract_code_from_response(raw_text)

            return {
                "success": True,
                "code": code,
                "raw_response": raw_text,
                "model_used": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "estimated_cost_usd": self._estimate_cost(model, response.usage),
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e), "model_used": model}

    async def generate_with_fallback(
        self,
        prompt: str,
        preferred_model: str,
        system_prompt: str,
        examples: list[str],
        user_api_key: Optional[str] = None,
    ) -> dict:
        """
        Try preferred model, fall back through chain if it fails.
        """
        models_to_try = [preferred_model] + [
            m for m in DEFAULT_FALLBACK_CHAIN if m != preferred_model
        ]

        for model in models_to_try:
            result = await self.generate_cad_code(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                examples=examples,
                user_api_key=user_api_key,
            )
            if result["success"]:
                result["fallback_used"] = model != preferred_model
                return result

        return {"success": False, "error": "All models failed", "tried": models_to_try}

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
        """
        if attempt > max_attempts:
            return {"success": False, "error": "Max correction attempts reached"}

        correction_prompt = f"""
The CadQuery code you generated failed with this error:
```
{error_message}
```

Your previous code:
```python
{failed_code}
```

Fix the error. Return ONLY the corrected complete Python code block.
Do not explain. Just the fixed code.

Common CadQuery fixes:
- Fillet too large: reduce fillet radius to < smallest edge length
- Non-manifold: ensure all solids are closed before boolean ops
- Zero-length edge: check that extrude distances are > 0
- Thread failure: use cq.Workplane.thread() with valid pitch
"""

        return await self.generate_cad_code(
            prompt=correction_prompt,
            model=model,
            system_prompt=system_prompt,
            examples=[],
            user_api_key=user_api_key,
        )

    def _resolve_api_key(self, model_config: dict, user_api_key: Optional[str]) -> Optional[str]:
        if model_config["type"] == "local":
            return None  # Ollama needs no key
        if user_api_key:
            return user_api_key  # User-provided key takes priority
        env_key = model_config.get("env_key")
        return os.getenv(env_key) if env_key else None

    def _get_api_base(self, model_config: dict) -> Optional[str]:
        if model_config["provider"] == "ollama":
            return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return None  # LiteLLM uses defaults for known providers

    def _estimate_cost(self, model: str, usage) -> float:
        config = SUPPORTED_MODELS.get(model, {})
        rate = config.get("cost_per_1k_tokens", 0.0)
        total_tokens = (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)
        return round((total_tokens / 1000) * rate, 6)
```

---

## 5. PROMPT FORMATTING PER MODEL

Different models have different quirks. This layer handles them:

```python
# backend/services/llm/prompt_formatter.py

def format_prompt_for_model(
    model: str,
    system_prompt: str,
    user_prompt: str,
    examples: list[str],
    model_config: dict,
) -> list[dict]:
    """
    Returns messages array formatted correctly for each model family.
    """
    provider = model_config["provider"]

    # Build the full user content
    examples_text = ""
    if examples:
        examples_text = "\n\nEXAMPLES OF CORRECT CADQUERY OUTPUT:\n"
        for i, ex in enumerate(examples[:2], 1):
            examples_text += f"\nExample {i}:\n```python\n{ex}\n```\n"

    full_user_content = f"{examples_text}\n\nNow generate CadQuery code for:\n{user_prompt}"

    # ── Ollama / local models ────────────────────────────────────
    # Local models perform better with system prompt embedded in user turn
    if provider == "ollama":
        return [
            {
                "role": "user",
                "content": f"[SYSTEM]\n{system_prompt}\n[/SYSTEM]\n\n{full_user_content}"
            }
        ]

    # ── Gemini ───────────────────────────────────────────────────
    # Gemini uses system_instruction differently — LiteLLM handles this
    # but we trim the system prompt to avoid Gemini safety refusals on
    # technical content like "explosion chamber" etc
    if provider == "google":
        safe_system = system_prompt.replace("combustion", "reaction").replace("explosive", "energetic")
        return [
            {"role": "system", "content": safe_system},
            {"role": "user", "content": full_user_content},
        ]

    # ── Reasoning models (DeepSeek R1, o1, o3) ───────────────────
    # These models do NOT use system prompts — inject into user turn
    reasoning_models = ["deepseek-r1", "o1", "o3", "o1-mini"]
    if any(rm in model for rm in reasoning_models):
        return [
            {
                "role": "user",
                "content": f"Instructions:\n{system_prompt}\n\n{full_user_content}"
            }
        ]

    # ── Standard (Claude, OpenAI, Groq, Mistral) ─────────────────
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_user_content},
    ]
```

---

## 6. RESPONSE PARSER

Models wrap code differently. This extracts it reliably:

```python
# backend/services/llm/response_parser.py

import re

def extract_code_from_response(raw_response: str) -> str:
    """
    Extract Python code from LLM response regardless of formatting.
    Models return code in many different ways — handle all of them.
    """
    # Pattern 1: ```python ... ``` (most common)
    python_block = re.search(r'```python\s*(.*?)```', raw_response, re.DOTALL)
    if python_block:
        return python_block.group(1).strip()

    # Pattern 2: ``` ... ``` (generic code block)
    generic_block = re.search(r'```\s*(.*?)```', raw_response, re.DOTALL)
    if generic_block:
        code = generic_block.group(1).strip()
        if "import cadquery" in code or "cq.Workplane" in code:
            return code

    # Pattern 3: Model returned raw code with no fences (some Ollama models)
    if "import cadquery" in raw_response or "cq.Workplane" in raw_response:
        # Find start of code
        lines = raw_response.split('\n')
        code_start = next(
            (i for i, line in enumerate(lines)
             if line.strip().startswith(("import", "#", "params", "result"))),
            0
        )
        return '\n'.join(lines[code_start:]).strip()

    # Pattern 4: Model explained then gave code — find the code section
    sections = raw_response.split('\n\n')
    for section in sections:
        if "cq.Workplane" in section:
            return section.strip()

    raise ValueError(
        f"Could not extract Python code from model response. "
        f"Raw response (first 500 chars): {raw_response[:500]}"
    )
```

---

## 7. THE GENERATE ENDPOINT

```python
# backend/routers/generate.py

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from ..services.llm.gateway import LLMGateway
from ..services.cad_executor import execute_cadquery_safe, validate_mesh
from ..services.ai_service import build_system_prompt, load_examples, extract_intent

router = APIRouter()
gateway = LLMGateway()

class GenerateRequest(BaseModel):
    prompt: str
    model: str = "gemini/gemini-2.0-flash"    # Default: fast + cheap
    domain: str = "mechanical"
    user_api_key: Optional[str] = None         # User-provided key
    enable_fallback: bool = True
    max_correction_attempts: int = 3

class GenerateResponse(BaseModel):
    job_id: str
    code: str
    params: dict
    files: dict                  # step_url, stl_url, obj_url
    mesh_stats: dict
    assumptions: list[str]
    warnings: list[str]
    model_used: str
    fallback_used: bool
    attempts: int
    cost_usd: float

@router.post("/generate", response_model=GenerateResponse)
async def generate_cad(request: GenerateRequest):
    # 1. Extract intent from prompt
    intent = await extract_intent(request.prompt, request.model)

    # 2. Build system prompt with domain context + examples
    system_prompt = build_system_prompt(domain=request.domain)
    examples = load_examples(part_type=intent.get("part_type", "generic"))

    # 3. Generate code via chosen LLM (with optional fallback)
    if request.enable_fallback:
        gen_result = await gateway.generate_with_fallback(
            prompt=request.prompt,
            preferred_model=request.model,
            system_prompt=system_prompt,
            examples=examples,
            user_api_key=request.user_api_key,
        )
    else:
        gen_result = await gateway.generate_cad_code(
            prompt=request.prompt,
            model=request.model,
            system_prompt=system_prompt,
            examples=examples,
            user_api_key=request.user_api_key,
        )

    if not gen_result["success"]:
        raise HTTPException(status_code=500, detail=gen_result["error"])

    code = gen_result["code"]
    attempts = 1

    # 4. Execute + self-correct loop
    for attempt in range(request.max_correction_attempts):
        exec_result = execute_cadquery_safe(code)

        if exec_result["success"]:
            break

        # Self-correct with the same model that generated the code
        correction = await gateway.self_correct(
            original_prompt=request.prompt,
            failed_code=code,
            error_message=exec_result["error"],
            model=gen_result["model_used"],
            system_prompt=system_prompt,
            user_api_key=request.user_api_key,
            attempt=attempt + 1,
        )

        if correction["success"]:
            code = correction["code"]
            attempts += 1
        else:
            break

    if not exec_result["success"]:
        raise HTTPException(
            status_code=422,
            detail=f"Could not generate valid geometry after {attempts} attempts: {exec_result['error']}"
        )

    # 5. Validate mesh
    mesh_stats = validate_mesh(exec_result["stl_path"])

    # 6. Upload to storage + return
    files = upload_to_storage(exec_result, job_id)

    return GenerateResponse(
        job_id=job_id,
        code=code,
        params=intent.get("dimensions", {}),
        files=files,
        mesh_stats=mesh_stats,
        assumptions=intent.get("ambiguities", []),
        warnings=mesh_stats.get("warnings", []),
        model_used=gen_result["model_used"],
        fallback_used=gen_result.get("fallback_used", False),
        attempts=attempts,
        cost_usd=gen_result["usage"].get("estimated_cost_usd", 0.0),
    )
```

---

## 8. MODELS LIST ENDPOINT (for the UI dropdown)

```python
# backend/routers/models.py

from fastapi import APIRouter
from ..config.models import SUPPORTED_MODELS
import subprocess

router = APIRouter()

@router.get("/models")
async def list_models():
    """
    Returns all supported models with availability status.
    Checks if Ollama is running and which models are pulled.
    """
    models = []
    ollama_available_models = get_available_ollama_models()

    for model_id, config in SUPPORTED_MODELS.items():
        available = True
        availability_note = None

        if config["type"] == "local":
            # Check if Ollama model is actually pulled
            model_name = model_id.replace("ollama/", "")
            available = model_name in ollama_available_models
            if not available:
                availability_note = f"Run: ollama pull {model_name}"

        models.append({
            "id": model_id,
            **config,
            "available": available,
            "availability_note": availability_note,
        })

    return {"models": models}

def get_available_ollama_models() -> list[str]:
    """Check which Ollama models are pulled and ready."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        return [line.split()[0] for line in lines if line]
    except Exception:
        return []  # Ollama not running
```

---

## 9. FRONTEND: MODEL SELECTOR COMPONENT

```tsx
// frontend/components/llm/ModelSelector.tsx

import { useState, useEffect } from "react"

type Model = {
  id: string
  display_name: string
  type: "local" | "api"
  provider: string
  cost_per_1k_tokens: number
  recommended_for: string[]
  available: boolean
  availability_note?: string
}

export function ModelSelector({
  selected,
  onSelect,
  userApiKeys,
}: {
  selected: string
  onSelect: (modelId: string) => void
  userApiKeys: Record<string, string>
}) {
  const [models, setModels] = useState<Model[]>([])

  useEffect(() => {
    fetch("/api/models").then(r => r.json()).then(d => setModels(d.models))
  }, [])

  const grouped = {
    local: models.filter(m => m.type === "local"),
    api: models.filter(m => m.type === "api"),
  }

  return (
    <div className="model-selector">
      <label>Model</label>

      <optgroup label="🖥️ Local (Ollama — Free, Private)">
        {grouped.local.map(m => (
          <ModelOption
            key={m.id} model={m}
            selected={selected === m.id}
            onSelect={onSelect}
            hasKey={true}  // local needs no key
          />
        ))}
      </optgroup>

      <optgroup label="☁️ API Models">
        {grouped.api.map(m => (
          <ModelOption
            key={m.id} model={m}
            selected={selected === m.id}
            onSelect={onSelect}
            hasKey={!!userApiKeys[m.provider]}
          />
        ))}
      </optgroup>
    </div>
  )
}

function ModelOption({ model, selected, onSelect, hasKey }) {
  const costLabel = model.cost_per_1k_tokens === 0
    ? "Free"
    : `$${(model.cost_per_1k_tokens * 1000).toFixed(3)}/1M tokens`

  return (
    <div
      onClick={() => model.available && hasKey && onSelect(model.id)}
      className={`model-option ${selected ? "selected" : ""} ${!model.available || !hasKey ? "disabled" : ""}`}
    >
      <span className="name">{model.display_name}</span>
      <span className="cost">{costLabel}</span>
      {!model.available && <span className="note">{model.availability_note}</span>}
      {!hasKey && model.type === "api" && <span className="note">Add API key in Settings</span>}
    </div>
  )
}
```

---

## 10. OLLAMA SETUP (Local Mode)

Users who want 100% local, free, private operation:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the best local models for CAD code generation:
ollama pull qwen2.5-coder:14b      # Best overall for code (recommended)
ollama pull codellama:13b           # Good alternative
ollama pull deepseek-coder:6.7b    # Fast, decent quality

# Verify it's running
ollama list

# The backend will auto-detect these via GET /models
```

```yaml
# docker-compose.ollama.yml — run Ollama as a service for deployment

version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes:
      - ollama-models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]   # GPU acceleration if available

  backend:
    build: ./backend
    environment:
      OLLAMA_BASE_URL: http://ollama:11434
    depends_on: [ollama]

volumes:
  ollama-models:
```

---

## 11. BENCHMARKING MODELS AGAINST EACH OTHER

Run this to find which model gives the best CAD accuracy for your use cases:

```python
# backend/tests/benchmarks/run_benchmark.py

import asyncio
import json
from pathlib import Path
from ...services.llm.gateway import LLMGateway
from ...services.cad_executor import execute_cadquery_safe, validate_mesh

BENCHMARK_PROMPTS = [
    {"id": "simple_bracket", "prompt": "Aluminum bracket 100x50mm, two M6 holes, 3mm thick"},
    {"id": "gear", "prompt": "Spur gear: 20 teeth, module 2, 15mm wide, 8mm center bore"},
    {"id": "hollow_sphere", "prompt": "Hollow sphere 60mm OD, 2mm wall, G1/4 threaded port"},
    {"id": "hex_bolt", "prompt": "M8 hex bolt, 40mm long, ISO 4762 standard"},
    {"id": "nozzle", "prompt": "Conical nozzle: 20mm inlet, 8mm throat, 30mm outlet, 45 degree half-angle"},
]

MODELS_TO_BENCHMARK = [
    "gemini/gemini-2.0-flash",
    "claude-haiku-4-5",
    "groq/llama-3.1-70b-versatile",
    "ollama/qwen2.5-coder:14b",
    "mistral/codestral-latest",
]

async def run_benchmark():
    gateway = LLMGateway()
    results = {}

    for model in MODELS_TO_BENCHMARK:
        model_results = []
        for test in BENCHMARK_PROMPTS:
            gen = await gateway.generate_cad_code(
                prompt=test["prompt"], model=model,
                system_prompt=load_system_prompt(),
                examples=load_examples("generic"),
            )
            if gen["success"]:
                exec_result = execute_cadquery_safe(gen["code"])
                if exec_result["success"]:
                    mesh = validate_mesh(exec_result["stl_path"])
                    model_results.append({
                        "test": test["id"],
                        "success": True,
                        "watertight": mesh["is_watertight"],
                        "volume_mm3": mesh["volume_mm3"],
                        "cost_usd": gen["usage"]["estimated_cost_usd"],
                        "tokens": gen["usage"]["prompt_tokens"] + gen["usage"]["completion_tokens"],
                    })
                else:
                    model_results.append({"test": test["id"], "success": False, "error": exec_result["error"]})
            else:
                model_results.append({"test": test["id"], "success": False, "error": gen["error"]})

        success_rate = sum(1 for r in model_results if r["success"]) / len(model_results)
        watertight_rate = sum(1 for r in model_results if r.get("watertight")) / len(model_results)
        total_cost = sum(r.get("cost_usd", 0) for r in model_results)

        results[model] = {
            "success_rate": f"{success_rate*100:.0f}%",
            "watertight_rate": f"{watertight_rate*100:.0f}%",
            "total_cost_usd": round(total_cost, 4),
            "tests": model_results,
        }
        print(f"{model}: {success_rate*100:.0f}% success, ${total_cost:.4f} total cost")

    Path("results/benchmark.json").write_text(json.dumps(results, indent=2))

asyncio.run(run_benchmark())
```

---

## 12. USER API KEY MANAGEMENT (Settings Page)

Users bring their own keys. Store them **client-side only** (never in your DB):

```tsx
// frontend/app/settings/page.tsx

const PROVIDERS = [
  { id: "anthropic",  label: "Anthropic (Claude)",  url: "https://console.anthropic.com", envHint: "ANTHROPIC_API_KEY" },
  { id: "google",     label: "Google (Gemini)",      url: "https://aistudio.google.com",  envHint: "GEMINI_API_KEY" },
  { id: "openai",     label: "OpenAI (GPT)",         url: "https://platform.openai.com",  envHint: "OPENAI_API_KEY" },
  { id: "groq",       label: "Groq (Llama/DeepSeek)",url: "https://console.groq.com",     envHint: "GROQ_API_KEY" },
  { id: "mistral",    label: "Mistral (Codestral)",   url: "https://console.mistral.ai",   envHint: "MISTRAL_API_KEY" },
]

// Store keys in localStorage (client-side only, never sent to your backend as plaintext)
// Keys are passed per-request in the request body (HTTPS encrypted)
// Never log them server-side
```

```python
# backend/services/llm/key_manager.py

import os

def get_api_key_for_model(model_config: dict, user_provided_key: str | None) -> str | None:
    """
    Key resolution priority:
    1. User-provided key (from request body)
    2. Environment variable (server default)
    3. None (for local/Ollama models)
    """
    if model_config["type"] == "local":
        return None

    if user_provided_key and len(user_provided_key) > 10:
        return user_provided_key

    env_var = model_config.get("env_key")
    if env_var:
        return os.getenv(env_var)

    return None

# SECURITY RULES:
# 1. NEVER log user API keys
# 2. NEVER store user API keys in DB
# 3. NEVER include user API keys in error messages
# 4. Keys are only held in memory for the duration of the request
```

---

## 13. ENVIRONMENT VARIABLES

```bash
# .env.example

# ── SERVER-SIDE API KEYS (your defaults — users can override) ──
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...
MISTRAL_API_KEY=...

# ── OLLAMA ─────────────────────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434

# ── DATABASE ───────────────────────────────────────────────────
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=...

# ── STORAGE ────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=ai-cad-models

# ── APP ────────────────────────────────────────────────────────
BACKEND_URL=http://localhost:8000
DEFAULT_MODEL=gemini/gemini-2.0-flash
CADQUERY_TIMEOUT_SECONDS=30
MAX_CORRECTION_ATTEMPTS=3
ENABLE_FALLBACK=true
```

---

## 14. REQUIREMENTS

```
# backend/requirements.txt

fastapi==0.115.0
uvicorn[standard]==0.30.0
cadquery==2.4.0
litellm==1.44.0          # ★ The unified LLM layer
pydantic==2.8.0
pydantic-settings==2.4.0
trimesh==4.4.0
python-dotenv==1.0.0
boto3==1.35.0
supabase==2.7.0
numpy==1.26.0
scipy==1.13.0
pytest==8.3.0
httpx==0.27.0
```

---

## 15. BUILD ORDER (Same 4-Phase Plan, Now Multi-LLM)

### Phase 1: Backend + LLM Gateway (Week 1)
```bash
pip install litellm cadquery fastapi uvicorn

# 1. Build config/models.py — the model registry
# 2. Build services/llm/gateway.py — LiteLLM wrapper
# 3. Build services/llm/prompt_formatter.py
# 4. Build services/llm/response_parser.py
# 5. Build cad_executor.py (unchanged from v1)
# 6. Wire /generate and /models endpoints
# 7. Test all models with pytest:
pytest tests/test_llm_gateway.py -v
```

### Phase 2: Frontend + Model Selector (Week 2)
```bash
# 8.  Build ModelSelector.tsx with live /models data
# 9.  Build ModelViewer.tsx (Three.js)
# 10. Build main generate/page.tsx
# 11. Build settings/page.tsx for API key entry
```

### Phase 3: Accuracy & Benchmarking (Week 3)
```bash
# 12. Run benchmark across all models: python run_benchmark.py
# 13. Use results to tune system prompt per model family
# 14. Add ParamPanel.tsx (sliders, no re-prompt)
# 15. Add Monaco code editor for manual edits
```

### Phase 4: Polish (Week 4)
```bash
# 16. Add ModelComparison.tsx — run same prompt on 2 models side-by-side
# 17. Add generation history
# 18. Deploy: Vercel + Railway
# 19. (Optional) Add Ollama as a Railway service for hosted local models
```

---

## 16. MODEL RECOMMENDATION CHEAT SHEET

| Use Case | Best Model | Why |
|---|---|---|
| Quick prototyping | `gemini/gemini-2.0-flash` | Cheapest API, fast, good enough |
| Maximum accuracy | `claude-sonnet-4` | Best instruction following + engineering reasoning |
| Zero cost, offline | `ollama/qwen2.5-coder:14b` | Best local code model |
| Complex math/geometry | `groq/deepseek-r1-distill-llama-70b` | Reasoning model, shows its work |
| Code specialist | `mistral/codestral-latest` | Trained specifically on code |
| Fastest response | `groq/llama-3.1-70b-versatile` | Groq hardware = very fast inference |
| Privacy-critical | Any `ollama/*` | Never leaves your machine |

---

*The entire system runs through `LLMGateway.generate_cad_code()`. Swap the model string, everything else stays the same. Add new models by adding an entry to `SUPPORTED_MODELS` — no other code changes needed.*