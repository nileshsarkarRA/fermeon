"""
Fermeon — Export Router
File download endpoints for STEP, STL, and OBJ files.
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from config.settings import settings

router = APIRouter()


@router.get("/files/{filename}")
async def download_file(filename: str):
    """
    Download a generated CAD file by filename (e.g., /files/abc123.step).
    Files are stored in the configured output directory.
    """
    # Security: ensure filename is safe (no path traversal)
    name = Path(filename).name
    if not name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only allow known CAD formats
    allowed_extensions = {".step", ".stl", ".obj", ".brep"}
    suffix = Path(name).suffix.lower()
    if suffix not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {suffix}")

    file_path = Path(settings.output_dir) / name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {name}")

    # Set appropriate MIME types
    media_types = {
        ".step": "application/step",
        ".stl": "model/stl",
        ".obj": "text/plain",
        ".brep": "application/octet-stream",
    }

    return FileResponse(
        path=str(file_path),
        filename=name,
        media_type=media_types.get(suffix, "application/octet-stream"),
    )


@router.get("/jobs/{job_id}/files")
async def list_job_files(job_id: str):
    """
    List all files generated for a specific job.
    """
    output_dir = Path(settings.output_dir)
    files = {}

    for ext in ["step", "stl", "obj"]:
        file_path = output_dir / f"{job_id}.{ext}"
        if file_path.exists():
            stat = file_path.stat()
            files[ext] = {
                "url": f"/files/{job_id}.{ext}",
                "size_bytes": stat.st_size,
                "filename": f"{job_id}.{ext}",
            }

    if not files:
        raise HTTPException(status_code=404, detail=f"No files found for job {job_id}")

    return {"job_id": job_id, "files": files}
