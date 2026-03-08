"""
Fermeon — Session Logger
Writes per-generation log files to backend/logs/{job_id}.json
Captures: prompt, model, token counts, elapsed time, attempts, cost, success/failure.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

LOGS_DIR = Path(__file__).parent.parent / "logs"


def write_session_log(
    job_id: str,
    prompt: str,
    model_used: str,
    enhance_usage: dict,
    gen_usage: dict,
    time_taken_s: float,
    attempts: int,
    success: bool,
    cost_usd: float,
    error: Optional[str] = None,
    model_type: str = "cloud",
    fallback_used: bool = False,
    detected_domain: Optional[str] = None,
    retry_history: Optional[list] = None,
    zero_tokens_detected: bool = False,
    enhanced_prompt: Optional[str] = None,
    generated_code: Optional[str] = None,
) -> str:
    """
    Write a session log entry to logs/{job_id}.json.
    Returns the URL path string (/api/logs/{job_id}).
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    ep = enhance_usage.get("prompt_tokens", 0) or 0
    ec = enhance_usage.get("completion_tokens", 0) or 0
    gp = gen_usage.get("prompt_tokens", 0) or 0
    gc = gen_usage.get("completion_tokens", 0) or 0

    log = {
        "job_id": job_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
        "model_used": model_used,
        "model_type": model_type,
        "detected_domain": detected_domain,
        "fallback_used": fallback_used,
        "tokens": {
            "enhance_prompt": ep,
            "enhance_completion": ec,
            "gen_prompt": gp,
            "gen_completion": gc,
            "total": ep + ec + gp + gc,
        },
        "time_taken_seconds": round(time_taken_s, 2),
        "attempts": attempts,
        "success": success,
        "cost_usd": cost_usd,
        "error": error,
        "zero_tokens_detected": zero_tokens_detected,
        "retry_history": retry_history or [],
        "enhanced_prompt": enhanced_prompt,
        "generated_code": generated_code,
    }

    log_path = LOGS_DIR / f"{job_id}.json"
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    return f"/api/logs/{job_id}"
