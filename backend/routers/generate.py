"""
Fermeon â€” Generate Router
POST /generate â€” main CAD generation endpoint.
Automatically routes to the zero-failure CEM pipeline when a model exists,
otherwise falls back to LLM code-generation with self-correction.

5-stage LLM pipeline (with terminal logging at each step):
  1. Prompt enhancement   â€” LLM trip 1 (Leap 71 enhancer)
  2. Code generation      â€” LLM trip 2
  3. Strip / extract      â€” parse raw response â†’ clean Python
  4. Syntax validation    â€” ast.parse()  (no subprocess)
  5. CadQuery execution   â€” subprocess sandbox; on failure â†’ self_correct â†’ repeat
     Max 3 total attempts before the job fails.
"""

from __future__ import annotations
import uuid
import os
import json
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from services.llm.gateway import LLMGateway
from services.cad_executor import execute_cadquery_safe, execute_cem_direct
from services.mesh_service import validate_mesh
from services.ai_service import build_system_prompt, load_examples, extract_intent
from services.llm.response_parser import validate_python_syntax
from services import pipeline_logger as plog
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
    enhance_prompt: bool = Field(default=True, description="Auto-enhance prompt before generation")


class GenerateResponse(BaseModel):
    job_id: str
    code: str
    params: dict
    files: dict
    mesh_stats: dict
    assumptions: List[str]
    warnings: List[str]
    model_used: str
    fallback_used: bool
    attempts: int
    cost_usd: float
    raw_response: Optional[str] = None
    log_url: Optional[str] = None
    enhanced_prompt: Optional[str] = None
    detected_domain: Optional[str] = None


# â”€â”€ CEM PIPELINE HELPER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _run_cem_pipeline(
    request: GenerateRequest,
    job_id: str,
    intent: dict,
    cem_class,
) -> GenerateResponse:
    """
    Leap 71 / Noyron-style zero-failure pipeline:
      1. LLM extracts JSON parameters from the user description
      2. Pydantic validates the params (falls back to defaults on bad LLM output)
      3. Human-written CEM builds the geometry â€” no LLM-generated CadQuery code
    CadQuery syntax errors are architecturally impossible on this path.
    """
    t_start = time.time()
    schema = cem_class.get_param_schema()

    # Pydantic v2 / v1 compatibility
    try:
        schema_dict = schema.model_json_schema()
    except AttributeError:
        schema_dict = schema.schema()

    plog.cem_banner(cem_class.__name__)

    plog.stage("extracting parameters", model=request.model)
    gen_result = await gateway.generate_cem_params(
        prompt=request.prompt,
        model=request.model,
        schema_json=json.dumps(schema_dict, indent=2),
        cem_name=intent.get("part_type", "object"),
        user_api_key=request.user_api_key,
    )

    params_dict: dict = gen_result.get("params") or {} if gen_result.get("success") else {}
    if gen_result.get("success"):
        usage = gen_result.get("usage", {})
        plog.ok(f"{usage.get('completion_tokens', '?')} tok", f"params: {list(params_dict.keys())[:5]}")
    else:
        plog.fail(gen_result.get("error", "param extraction failed â€” using defaults"))

    # Validate â€” fall back to schema defaults if LLM output is unusable
    try:
        validated_params = schema(**params_dict)
    except Exception:
        validated_params = schema()

    plog.stage("building geometry (CEM)")
    exec_result = execute_cem_direct(
        cem_class=cem_class,
        params=validated_params,
        job_id=job_id,
    )

    if not exec_result.get("success"):
        plog.fail(exec_result.get("error", "CEM build failed"))
        raise HTTPException(
            status_code=500,
            detail={
                "message": "CEM geometry build failed",
                "error": exec_result.get("error", "Unknown error"),
                "code": f"# CEM: {cem_class.__name__}\n# Params: {params_dict}",
                "attempts": 1,
            },
        )

    elapsed = time.time() - t_start
    plog.final_success(job_id, exec_result.get("paths", {}), 1, elapsed)

    stl_path = exec_result.get("paths", {}).get("stl", "")
    mesh_stats = validate_mesh(stl_path) if stl_path and os.path.exists(stl_path) else {}

    files: dict = {}
    for fmt, path in exec_result.get("paths", {}).items():
        if path and os.path.exists(path):
            files[f"{fmt}_url"] = f"/files/{job_id}.{fmt}"

    try:
        params_repr = validated_params.model_dump()
    except AttributeError:
        params_repr = validated_params.dict()

    readable_code = (
        f"# Fermeon CEM Pipeline \u2014 {cem_class.__name__}\n"
        f"# Zero syntax errors: geometry built from validated engineering parameters\n\n"
        f"from cem.factory import get_cem_class\n\n"
        f"cem_class = get_cem_class('{intent.get('part_type', 'object')}')\n"
        f"params = cem_class.get_param_schema()(**{json.dumps(params_repr, indent=4)})\n"
        f"result = cem_class(params).build()\n"
    )

    usage = gen_result.get("usage", {}) if gen_result.get("success") else {}

    return GenerateResponse(
        job_id=job_id,
        code=readable_code,
        params=params_repr,
        files=files,
        mesh_stats=mesh_stats,
        assumptions=[f"CEM pipeline: {cem_class.__name__} (human-written geometry, zero-failure)"],
        warnings=mesh_stats.get("warnings", []),
        model_used=request.model,
        fallback_used=False,
        attempts=1,
        cost_usd=usage.get("estimated_cost_usd", 0.0),
        raw_response=gen_result.get("raw_response") if gen_result.get("success") else None,
        log_url=None,
        enhanced_prompt=None,
        detected_domain=intent.get("domain"),
    )


# â”€â”€ MAIN GENERATE ENDPOINT â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/generate", response_model=GenerateResponse)
async def generate_cad(request: GenerateRequest):
    """
    Generate CAD from a natural language prompt.

    Pipeline:
      Stage 1 â€” Prompt enhancement  (LLM trip 1, optional)
      Stage 2 â€” Code generation     (LLM trip 2)
      Stage 3 â€” Strip / extract     (response parser)
      Stage 4 â€” Syntax validation   (ast.parse â€” no subprocess)
      Stage 5 â€” CadQuery execution  (subprocess sandbox)
      On failure â†’ self_correct â†’ repeat (max 3 total attempts)

    Auto-routes to the zero-failure CEM pipeline when a model exists for the
    requested object; otherwise uses the LLM code-generation path above.
    """
    job_id = str(uuid.uuid4())[:12]
    t_start = time.time()

    # Fast local intent extraction (no LLM needed)
    intent = extract_intent(request.prompt, request.model)

    # â”€â”€ CEM fast-path â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    from cem.factory import get_cem_class
    cem_class = get_cem_class(intent.get("part_type", ""))
    if cem_class:
        plog.job_start(job_id, request.prompt)
        return await _run_cem_pipeline(request, job_id, intent, cem_class)

    # â”€â”€ LLM code-generation path â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    plog.job_start(job_id, request.prompt)

    system_prompt = build_system_prompt(domain=request.domain or intent["domain"])
    examples = load_examples(part_type=intent.get("part_type", "generic"))

    # â”€â”€ Stage 1: Enhance prompt â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    enhanced_prompt = request.prompt
    if request.enhance_prompt:
        plog.stage("enhancing prompt", model=request.model)
        enh = await gateway.enhance_prompt_text(
            prompt=request.prompt,
            model=request.model,
            user_api_key=request.user_api_key,
        )
        if enh.get("enhanced_prompt"):
            enhanced_prompt = enh["enhanced_prompt"]
        if enh.get("success"):
            usage = enh.get("usage", {})
            plog.ok(f"{usage.get('completion_tokens', '?')} tok")
        else:
            plog.fail(f"{enh.get('error', 'enhance failed')} â€” using original prompt")

    # â”€â”€ Stages 2â€“5: Generate â†’ Strip â†’ Validate â†’ Execute (max N attempts) â”€â”€â”€â”€
    model_used = request.model
    fallback_used = False
    total_attempts = 0
    last_error = ""
    last_code = ""
    exec_result: dict | None = None
    total_cost = 0.0

    MAX = request.max_correction_attempts

    for attempt_n in range(1, MAX + 1):
        plog.attempt_header(attempt_n, MAX)
        t_attempt = time.time()

        # â”€â”€ Stage 2: Generate code â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if attempt_n == 1:
            # First attempt: fresh generation (with optional fallback chain)
            plog.stage("generating", model=request.model, extra=f" (timeout=250s)")
            if request.enable_fallback:
                gen_result = await gateway.generate_with_fallback(
                    prompt=enhanced_prompt,
                    preferred_model=request.model,
                    system_prompt=system_prompt,
                    examples=examples,
                    user_api_key=request.user_api_key,
                )
            else:
                gen_result = await gateway.generate_cad_code(
                    prompt=enhanced_prompt,
                    model=request.model,
                    system_prompt=system_prompt,
                    examples=examples,
                    user_api_key=request.user_api_key,
                )
        else:
            # Subsequent attempts: self-correct with the previous error
            plog.stage("regenerating (self-correct)", model=model_used)
            gen_result = await gateway.self_correct(
                original_prompt=enhanced_prompt,
                failed_code=last_code,
                error_message=last_error,
                model=model_used,
                system_prompt=system_prompt,
                user_api_key=request.user_api_key,
                attempt=attempt_n,
                max_attempts=MAX,
            )

        total_attempts += 1

        if not gen_result.get("success"):
            last_error = gen_result.get("error", "LLM generation failed")
            plog.fail(last_error)
            continue

        model_used = gen_result.get("model_used", model_used)
        fallback_used = fallback_used or gen_result.get("fallback_used", False)
        usage = gen_result.get("usage", {})
        total_cost += usage.get("estimated_cost_usd", 0.0)
        gen_elapsed = time.time() - t_attempt
        plog.ok(f"{usage.get('completion_tokens', '?')} tok  {gen_elapsed:.1f}s")

        # â”€â”€ Stage 3: Strip / extract â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        plog.stage("stripping response")
        code = gen_result.get("code", "")
        lines = len(code.splitlines())
        plog.ok(f"extracted {lines} lines")

        # â”€â”€ Stage 4: Validate Python syntax â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        plog.stage("validating Python syntax")
        syntax_ok, syntax_err = validate_python_syntax(code)
        if not syntax_ok:
            last_error = f"Syntax error â€” {syntax_err}"
            last_code = code
            plog.fail(last_error)
            continue
        plog.ok("syntax OK")

        # â”€â”€ Stage 5: Execute CadQuery â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        plog.stage("executing CadQuery")
        exec_result = execute_cadquery_safe(code=code, job_id=job_id)

        if exec_result.get("success"):
            plog.ok("geometry built â€” step + stl exported")
            break

        last_error = exec_result.get("error", "CadQuery execution failed")
        last_code = code
        plog.fail(last_error)

    # â”€â”€ Final outcome â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elapsed = time.time() - t_start

    if not exec_result or not exec_result.get("success"):
        plog.final_failure(total_attempts, last_error)
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Could not generate valid geometry after {total_attempts} attempt(s)",
                "error": last_error,
                "code": last_code,
                "attempts": total_attempts,
            },
        )

    plog.final_success(job_id, exec_result.get("paths", {}), total_attempts, elapsed)

    # â”€â”€ Build response â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    stl_path = exec_result.get("paths", {}).get("stl", "")
    mesh_stats = validate_mesh(stl_path) if stl_path and os.path.exists(stl_path) else {}

    files: dict = {}
    for fmt, path in exec_result.get("paths", {}).items():
        if path and os.path.exists(path):
            files[f"{fmt}_url"] = f"/files/{job_id}.{fmt}"

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
        attempts=total_attempts,
        cost_usd=total_cost,
        raw_response=gen_result.get("raw_response"),
        log_url=None,
        enhanced_prompt=enhanced_prompt if enhanced_prompt != request.prompt else None,
        detected_domain=intent.get("domain"),
    )


# â”€â”€ CEM ENDPOINT (explicit toggle) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/generate/cem", response_model=GenerateResponse)
async def generate_cad_cem(request: GenerateRequest):
    """
    Explicit Leap 71 / Noyron CEM endpoint.
    Raises 400 if no CEM exists for the requested object type.
    The main /generate endpoint automatically delegates here when a CEM is available.
    """
    job_id = str(uuid.uuid4())[:12]
    intent = extract_intent(request.prompt, request.model)

    from cem.factory import get_cem_class
    cem_class = get_cem_class(intent.get("part_type", ""))

    if not cem_class:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No Computational Engineering Model exists for "
                f"'{intent.get('part_type', 'this object')}' yet. "
                f"Use /api/generate for LLM code-generation fallback."
            ),
        )

    plog.job_start(job_id, request.prompt)
    return await _run_cem_pipeline(request, job_id, intent, cem_class)


