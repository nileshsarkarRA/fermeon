"""
Fermeon — Logs Router
GET /api/logs/{job_id} — download a session log JSON file.
"""

from __future__ import annotations
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()

LOGS_DIR = Path(__file__).parent.parent / "logs"

_JOB_ID_RE = re.compile(r'^[a-f0-9\-]{4,36}$')


@router.get("/logs/{job_id}")
async def get_session_log(job_id: str):
    """Download the session log JSON for a completed generation job."""
    # Validate to prevent path traversal
    if not _JOB_ID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    log_path = LOGS_DIR / f"{job_id}.json"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log not found for this job")

    return FileResponse(
        path=str(log_path),
        media_type="application/json",
        filename=f"fermeon_session_{job_id}.json",
    )
