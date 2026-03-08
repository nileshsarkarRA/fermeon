"""
Fermeon — Mesh Validation Service
Uses trimesh to validate exported STL files for watertightness, volume, etc.
"""

import json
from pathlib import Path
from typing import Optional


def validate_mesh(stl_path: str) -> dict:
    """
    Validate an STL file using trimesh.
    Returns mesh statistics and quality checks.
    """
    try:
        import trimesh
        import numpy as np

        mesh = trimesh.load(stl_path)

        if isinstance(mesh, trimesh.Scene):
            # Multi-body scene — combine all meshes
            meshes = list(mesh.geometry.values())
            if not meshes:
                return _error_stats("Empty scene — no geometry exported")
            mesh = trimesh.util.concatenate(meshes)

        if not isinstance(mesh, trimesh.Trimesh):
            return _error_stats("Could not load as triangle mesh")

        is_watertight = mesh.is_watertight
        volume = float(mesh.volume) if is_watertight else 0.0
        surface_area = float(mesh.area)
        face_count = len(mesh.faces)
        vertex_count = len(mesh.vertices)

        warnings = []
        if not is_watertight:
            warnings.append("Mesh is not watertight — may have open edges or non-manifold geometry")
        if face_count > 500_000:
            warnings.append(f"High polygon count ({face_count:,} faces) may slow 3D viewer")
        if volume < 0:
            warnings.append("Negative volume detected — normals may be inverted")

        bounds = mesh.bounds
        bounding_box = {
            "x": float(bounds[1][0] - bounds[0][0]),
            "y": float(bounds[1][1] - bounds[0][1]),
            "z": float(bounds[1][2] - bounds[0][2]),
        }

        # File size
        file_size_bytes = Path(stl_path).stat().st_size

        return {
            "success": True,
            "is_watertight": is_watertight,
            "volume_mm3": round(volume, 3),
            "surface_area_mm2": round(surface_area, 3),
            "face_count": face_count,
            "vertex_count": vertex_count,
            "bounding_box_mm": bounding_box,
            "file_size_bytes": file_size_bytes,
            "warnings": warnings,
        }

    except ImportError:
        return {
            "success": False,
            "is_watertight": None,
            "volume_mm3": 0,
            "surface_area_mm2": 0,
            "face_count": 0,
            "vertex_count": 0,
            "bounding_box_mm": {},
            "file_size_bytes": 0,
            "warnings": ["trimesh not installed — install with: pip install trimesh"],
        }
    except Exception as e:
        return _error_stats(f"Mesh validation failed: {str(e)}")


def _error_stats(error: str) -> dict:
    return {
        "success": False,
        "is_watertight": False,
        "volume_mm3": 0,
        "surface_area_mm2": 0,
        "face_count": 0,
        "vertex_count": 0,
        "bounding_box_mm": {},
        "file_size_bytes": 0,
        "warnings": [error],
    }
