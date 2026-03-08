"""
Fermeon — Generate Router
POST /generate — main CAD generation endpoint with self-correction loop.
"""

from __future__ import annotations
import uuid
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from services.llm.gateway import LLMGateway
from services.cad_executor import execute_cadquery_safe
from services.mesh_service import validate_mesh
from services.ai_service import build_system_prompt, load_examples, extract_intent
from config.models import SUPPORTED_MODELS

router = APIRouter()
gateway = LLMGateway()


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="Natural language description of the part")
    model: str = Field(default="gemini/gemini-2.0-flash", description="LLM model to use")
    domain: str = Field(default="mechanical", description="Engineering domain context")
    user_api_key: Optional[str] = Field(default=None, description="User-provided API key")
    enable_fallback: bool = Field(default=True, description="Enable automatic model fallback")
    max_correction_attempts: int = Field(default=3, ge=1, le=5)


class GenerateResponse(BaseModel):
    job_id: str
    code: str
    params: dict
    files: dict                  # step_url, stl_url
    mesh_stats: dict
    assumptions: List[str]
    warnings: List[str]
    model_used: str
    fallback_used: bool
    attempts: int
    cost_usd: float
    raw_response: Optional[str] = None


@router.post("/generate", response_model=GenerateResponse)
async def generate_cad(request: GenerateRequest):
    """
    Generate CadQuery code from a natural language prompt.
    Handles LLM call → execution → self-correction → file export.
    """
    job_id = str(uuid.uuid4())[:12]

    # 1. Extract intent from prompt (fast, local — no LLM needed)
    intent = extract_intent(request.prompt, request.model)

    # 2. Build system prompt with domain context + load few-shot examples
    system_prompt = build_system_prompt(domain=request.domain or intent["domain"])
    examples = load_examples(part_type=intent.get("part_type", "generic"))

    # 3. Generate code via chosen LLM (with optional fallback chain)
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

    if not gen_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Code generation failed: {gen_result.get('error', 'Unknown error')}"
        )

    code = gen_result["code"]
    model_used = gen_result["model_used"]
    fallback_used = gen_result.get("fallback_used", False)
    attempts = 1
    exec_result = None

    # 4. Execute + self-correct loop
    for attempt in range(request.max_correction_attempts):
        exec_result = execute_cadquery_safe(code=code, job_id=job_id)

        if exec_result.get("success"):
            break

        if attempt < request.max_correction_attempts - 1:
            correction = await gateway.self_correct(
                original_prompt=request.prompt,
                failed_code=code,
                error_message=exec_result.get("error", "Unknown execution error"),
                model=model_used,
                system_prompt=system_prompt,
                user_api_key=request.user_api_key,
                attempt=attempt + 1,
                max_attempts=request.max_correction_attempts,
            )

            if correction.get("success"):
                code = correction["code"]
                attempts += 1
            else:
                break

    if not exec_result or not exec_result.get("success"):
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Could not generate valid geometry after {attempts} attempt(s)",
                "error": exec_result.get("error") if exec_result else "Execution did not run",
                "code": code,
                "attempts": attempts,
            }
        )

    # 5. Validate mesh
    stl_path = exec_result.get("paths", {}).get("stl", "")
    mesh_stats = validate_mesh(stl_path) if stl_path and os.path.exists(stl_path) else {}

    # 6. Build file URLs for frontend
    files = {}
    paths = exec_result.get("paths", {})
    for fmt, path in paths.items():
        if path and os.path.exists(path):
            files[f"{fmt}_url"] = f"/files/{job_id}.{fmt}"

    usage = gen_result.get("usage", {})

    return GenerateResponse(
        job_id=job_id,
        code=code,
        params=intent.get("dimensions", {}),
        files=files,
        mesh_stats=mesh_stats,
        assumptions=intent.get("ambiguities", []),
        warnings=mesh_stats.get("warnings", []),
        model_used=model_used,
        fallback_used=fallback_used,
        attempts=attempts,
        cost_usd=usage.get("estimated_cost_usd", 0.0),
        raw_response=gen_result.get("raw_response"),
    )
