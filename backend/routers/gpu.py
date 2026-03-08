"""
Fermeon — GPU Detection Endpoint
Checks for NVIDIA GPU availability for Ollama acceleration.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/gpu-info")
async def get_gpu_info():
    """
    Detect NVIDIA GPU for Ollama acceleration.
    Returns GPU info that the frontend displays in Settings.
    """
    gpu_info = {
        "available": False,
        "name": None,
        "vram_gb": None,
        "cuda_version": None,
        "ollama_will_use_gpu": False,
        "note": None,
    }

    # Method 1: Try nvidia-smi via subprocess
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(', ')
            if len(parts) >= 2:
                gpu_info["available"] = True
                gpu_info["name"] = parts[0].strip()
                gpu_info["vram_gb"] = round(int(parts[1].strip()) / 1024, 1)
                gpu_info["ollama_will_use_gpu"] = True
                gpu_info["note"] = f"Ollama will auto-use {gpu_info['name']} via CUDA"
                return gpu_info
    except Exception:
        pass

    # Method 2: Try torch (if installed)
    try:
        import torch
        if torch.cuda.is_available():
            gpu_info["available"] = True
            gpu_info["name"] = torch.cuda.get_device_name(0)
            gpu_info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
            gpu_info["cuda_version"] = torch.version.cuda
            gpu_info["ollama_will_use_gpu"] = True
            gpu_info["note"] = f"CUDA {gpu_info['cuda_version']} · {gpu_info['name']}"
            return gpu_info
    except Exception:
        pass

    gpu_info["note"] = "No NVIDIA GPU detected — Ollama will use CPU (slower but works)"
    return gpu_info
