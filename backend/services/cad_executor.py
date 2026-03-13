"""
Fermeon — Safe CadQuery Executor
Executes LLM-generated CadQuery code in a restricted subprocess with timeout.
Exports STEP + STL + OBJ files.

v2: adds post-execution bounding-box sanity check via domain_bounds.py
"""

import subprocess
import sys
import os
import tempfile
import uuid
import json
from pathlib import Path
from typing import Optional
from config.settings import settings
from config.domain_bounds import get_bounds


# Template that wraps generated CadQuery code to ensure proper export
EXECUTION_TEMPLATE = '''
import cadquery as cq
import sys
import json
import traceback

OUTPUT_DIR = "{output_dir}"
JOB_ID = "{job_id}"

# ── USER CODE ─────────────────────────────────────────────────
{user_code}
# ── END USER CODE ─────────────────────────────────────────────

# Try to find the result object
result_obj = None
for var_name in ["result", "part", "assembly", "shape", "solid", "model"]:
    if var_name in dir():
        candidate = eval(var_name)
        if hasattr(candidate, "val") or hasattr(candidate, "objects"):
            result_obj = candidate
            break

if result_obj is None:
    # Try last assigned Workplane or Shape in local vars
    import cadquery
    for name, obj in list(locals().items()):
        if isinstance(obj, (cadquery.Workplane, cadquery.Assembly)):
            result_obj = obj

if result_obj is None:
    print(json.dumps({{"success": False, "error": "No result object found. Assign your final geometry to a variable named 'result'."}}))
    sys.exit(1)

try:
    paths = {{}}

    # Export STEP
    step_path = f"{{OUTPUT_DIR}}/{{JOB_ID}}.step"
    cq.exporters.export(result_obj, step_path, cq.exporters.ExportTypes.STEP)
    paths["step"] = step_path

    # Export STL
    stl_path = f"{{OUTPUT_DIR}}/{{JOB_ID}}.stl"
    cq.exporters.export(result_obj, stl_path, cq.exporters.ExportTypes.STL)
    paths["stl"] = stl_path

    # Export as BREP (better for complex solids - optional)
    # brep_path = f"{{OUTPUT_DIR}}/{{JOB_ID}}.brep"
    # cq.exporters.export(result_obj, brep_path, "BREP")
    # paths["brep"] = brep_path

    print(json.dumps({{"success": True, "paths": paths, "job_id": JOB_ID}}))

except Exception as e:
    print(json.dumps({{"success": False, "error": f"Export failed: {{traceback.format_exc()}}"}}))
    sys.exit(1)
'''


def execute_cadquery_safe(
    code: str,
    job_id: Optional[str] = None,
    output_dir: Optional[str] = None,
    timeout: Optional[int] = None,
    domain: Optional[str] = None,
) -> dict:
    """
    Execute CadQuery code in a subprocess with timeout.
    Optionally checks geometry bounding-box against domain-expected size range.
    Returns: {success, paths, error, job_id}
    """
    job_id = job_id or str(uuid.uuid4())[:8]
    output_dir = output_dir or settings.output_dir
    timeout = timeout or settings.cadquery_timeout_seconds

    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Build the full script
    script = EXECUTION_TEMPLATE.format(
        output_dir=output_dir.replace('\\', '/'),
        job_id=job_id,
        user_code=code,
    )

    # Write to temp file
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False, encoding='utf-8'
    ) as f:
        f.write(script)
        script_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
        )

        # Parse JSON output from the script
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if not stdout:
            return {
                "success": False,
                "error": f"No output from executor. stderr: {stderr[:1000]}",
                "job_id": job_id,
            }

        # Find the last JSON line in stdout
        json_lines = [l for l in stdout.split('\n') if l.strip().startswith('{')]
        if not json_lines:
            return {
                "success": False,
                "error": f"Could not parse executor output. stdout: {stdout[:500]}, stderr: {stderr[:500]}",
                "job_id": job_id,
            }

        exec_result = json.loads(json_lines[-1])
        exec_result["job_id"] = job_id
        if stderr and not exec_result.get("success"):
            exec_result["stderr"] = stderr[:500]

        # ── Bounding-box sanity check ────────────────────────────────────────
        if exec_result.get("success") and domain:
            bbox_warn = _check_bounding_box(
                exec_result.get("paths", {}).get("step", ""),
                domain,
            )
            if bbox_warn:
                # Treat as a failure so self-correction can fix scale issues
                return {
                    "success": False,
                    "error": bbox_warn,
                    "job_id": job_id,
                }

        return exec_result

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"CadQuery execution timed out after {timeout}s. Simplify the geometry or increase timeout.",
            "job_id": job_id,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Executor error: {str(e)}",
            "job_id": job_id,
        }
    finally:
        # Clean up temp script
        try:
            os.unlink(script_path)
        except Exception:
            pass


def _check_bounding_box(step_path: str, domain: str) -> str:
    """
    Import the generated STEP file and verify its bounding-box is within
    the expected range for the domain.
    Returns an error string if out-of-range, empty string if OK or check unavailable.
    """
    if not step_path or not os.path.exists(step_path):
        return ""

    try:
        import cadquery as cq
        bounds = get_bounds(domain)
        result_obj = cq.importers.importStep(step_path)
        bb = result_obj.val().BoundingBox()
        max_dim = max(bb.xlen, bb.ylen, bb.zlen)

        if max_dim < bounds["min"]:
            return (
                f"Geometry too small for domain '{domain}': "
                f"largest dimension is {max_dim:.2f}mm but minimum expected is {bounds['min']}mm. "
                f"Check that all dimensions use mm (not meters or cm) and are realistic."
            )
        if max_dim > bounds["max"]:
            return (
                f"Geometry too large for domain '{domain}': "
                f"largest dimension is {max_dim:.2f}mm but maximum expected is {bounds['max']}mm. "
                f"Check dimension values — possible unit confusion (meters vs mm) or off-by-1000 error."
            )
        return ""

    except Exception:
        # Never let bbox check crash the pipeline — just skip if CQ import fails
        return ""



def execute_cem_direct(
    cem_class,
    params,
    job_id: str,
    output_dir: Optional[str] = None,
) -> dict:
    """
    Execute a Computational Engineering Model directly in-process.
    Since CEMs are human-written, trusted code there is no need for subprocess sandboxing.
    This is faster, simpler, and gives better error messages than the subprocess path.
    Returns: {success, paths: {step, stl}, job_id, error?}
    """
    import traceback
    import cadquery as cq

    output_dir = output_dir or settings.output_dir
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        instance = cem_class(params)
        result = instance.build()

        paths: dict[str, str] = {}

        step_path = os.path.join(output_dir, f"{job_id}.step")
        cq.exporters.export(result, step_path, cq.exporters.ExportTypes.STEP)
        paths["step"] = step_path

        stl_path = os.path.join(output_dir, f"{job_id}.stl")
        cq.exporters.export(result, stl_path, cq.exporters.ExportTypes.STL)
        paths["stl"] = stl_path

        return {"success": True, "paths": paths, "job_id": job_id}

    except Exception:
        return {
            "success": False,
            "error": traceback.format_exc(),
            "job_id": job_id,
        }
