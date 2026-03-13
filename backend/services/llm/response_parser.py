"""
Fermeon — Response Parser
Extracts Python/CadQuery code from LLM responses regardless of formatting.
Models wrap code in wildly different ways — this handles all of them.
"""

import ast
import re
import json
from typing import Optional, Tuple


def extract_code_from_response(raw_response: str) -> str:
    """
    Extract Python code from LLM response regardless of formatting.

    Handles:
    - ```python ... ``` blocks (most common)
    - ``` ... ``` generic blocks
    - Raw code with no fences (some Ollama models)
    - Code embedded in explanation text
    - Reasoning model <think>...</think> prefixes (DeepSeek R1)
    """
    if not raw_response or not raw_response.strip():
        raise ValueError("Empty response from model")

    # Strip DeepSeek R1 / reasoning model <think> blocks
    raw_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()

    # Pattern 1: ```python ... ``` (most common — Claude, GPT, Gemini)
    python_block = re.search(r'```python\s*(.*?)```', raw_response, re.DOTALL)
    if python_block:
        code = python_block.group(1).strip()
        code = _auto_fix_cq_imports(code)
        code = _auto_alias_result(code)
        code = _strip_display_calls(code)
        if _looks_like_cadquery(code):
            return code

    # Pattern 2: ``` ... ``` (generic code block)
    generic_block = re.search(r'```(?:\w+)?\s*(.*?)```', raw_response, re.DOTALL)
    if generic_block:
        code = generic_block.group(1).strip()
        code = _auto_fix_cq_imports(code)
        code = _auto_alias_result(code)
        code = _strip_display_calls(code)
        if _looks_like_cadquery(code):
            return code

    # Pattern 3: Raw code with no fences (some Ollama models emit bare code)
    if _looks_like_cadquery(raw_response):
        lines = raw_response.split('\n')
        code_start = next(
            (i for i, line in enumerate(lines)
             if line.strip().startswith(("import", "#", "params", "result", "cq.", "from cadquery"))),
            0
        )
        code = '\n'.join(lines[code_start:]).strip()
        code = _auto_fix_cq_imports(code)
        code = _auto_alias_result(code)
        code = _strip_display_calls(code)
        return code

    # Pattern 4: Code embedded in explanation — find the code section
    sections = raw_response.split('\n\n')
    for section in sections:
        if _looks_like_cadquery(section):
            code = section.strip()
            code = _auto_fix_cq_imports(code)
            code = _auto_alias_result(code)
            code = _strip_display_calls(code)
            return code

    # Pattern 5: Check if there's ANY python import cadquery block
    any_block = re.search(r'(import cadquery.*)', raw_response, re.DOTALL)
    if any_block:
        code = any_block.group(1).strip()
        code = _auto_fix_cq_imports(code)
        code = _auto_alias_result(code)
        code = _strip_display_calls(code)
        return code

    raise ValueError(
        f"Could not extract CadQuery Python code from model response. "
        f"First 500 chars: {raw_response[:500]!r}"
    )


def _looks_like_cadquery(text: str) -> bool:
    """Check if text contains recognizable CadQuery code."""
    cadquery_markers = [
        "import cadquery",
        "cq.Workplane",
        "cadquery.Workplane",
        "import cq",
        "from cadquery",
        ".extrude(",
        ".revolve(",
        ".sphere(",
        ".box(",
        ".cylinder(",
        ".shell(",
        ".fillet(",
        ".chamfer(",
        "cq.Assembly",
    ]
    return any(marker in text for marker in cadquery_markers)


def _auto_fix_cq_imports(code: str) -> str:
    """
    Silently fix common LLM import mistakes:
    - 'from cadquery import Workplane, ...' → remove, add 'import cadquery as cq'
    - Bare 'Workplane(' → 'cq.Workplane('
    - 'cq.WorkPlane(' → 'cq.Workplane('  (capitalisation fix)
    - Remove forbidden imports (numpy, pyvista, etc.) and replace with comment
    """
    # Remove forbidden imports that will crash executor
    forbidden_imports = [
        "import numpy",
        "import pyvista",
        "import trimesh",
        "import vtk",
        "import FreeCAD",
        "import OCC",
        "import scipy",
        "import shapely",
        "import matplotlib",
        "from numpy",
        "from pyvista",
        "from trimesh",
        "from OCC",
    ]
    for bad_import in forbidden_imports:
        code = re.sub(
            rf'^{re.escape(bad_import)}[^\n]*\n?',
            '# [auto-removed forbidden import: only cadquery and math allowed]\n',
            code,
            flags=re.MULTILINE
        )

    # Remove bad from-imports for cadquery itself
    code = re.sub(r'from cadquery import[^\n]*\n', '', code)

    # Ensure correct import is present
    if 'import cadquery as cq' not in code and 'import cadquery' in code:
        code = re.sub(r'import cadquery\b', 'import cadquery as cq', code)
    elif 'import cadquery as cq' not in code and 'cq.Workplane' in code:
        code = 'import cadquery as cq\n' + code

    # Prefix bare CadQuery class names
    for cls in ('Workplane', 'Assembly', 'Vector', 'Edge', 'Face', 'Shell', 'Solid'):
        code = re.sub(rf'(?<!cq\.)\b{cls}\(', f'cq.{cls}(', code)

    # Fix capitalisation typos
    code = re.sub(r'\bcq\.WorkPlane\b', 'cq.Workplane', code)
    code = re.sub(r'\bcq\.workplane\b', 'cq.Workplane', code)

    return code


def _strip_display_calls(code: str) -> str:
    """Remove Jupyter/CQ-editor display calls that crash in subprocess."""
    patterns = [
        r'\bshow_object\s*\([^)]*\)\s*\n?',
        r'\bdisplay\s*\([^)]*\)\s*\n?',
        r'\bshow\s*\([^)]*\)\s*\n?',
        r'\bcq\.exporters\.export\s*\([^)]*\)\s*\n?',
    ]
    for pat in patterns:
        code = re.sub(pat, '', code)
    return code


def _auto_alias_result(code: str) -> str:
    """
    If the code has no 'result = ...' assignment, find the last WorkPlane
    variable assigned and alias it as 'result'.
    """
    if 'result' in code:
        return code

    # Find last Workplane assignment like: varname = cq.Workplane(...)...
    matches = list(re.finditer(r'^(\w+)\s*=\s*(?:cq\.Workplane|cq\.Assembly)', code, re.MULTILINE))
    if matches:
        last_var = matches[-1].group(1)
        if last_var != 'result':
            code += f'\n\nresult = {last_var}\n'
    return code


def validate_python_syntax(code: str) -> Tuple[bool, str]:
    """
    Check whether a code string is valid Python using the AST parser.
    Also performs CadQuery-specific static safety validation.
    Returns (True, "") on success, (False, error_description) on failure.
    """
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return False, f"line {exc.lineno}: {exc.msg}"
    except Exception as exc:
        return False, str(exc)

    # CadQuery-specific safety checks
    try:
        _validate_code_safety(code)
    except ValueError as exc:
        return False, str(exc)

    return True, ""


def _validate_code_safety(code: str) -> None:
    """
    Static analysis for patterns that always produce wrong geometry or crashes.
    Raises ValueError with a descriptive message if a bad pattern is found.
    """
    # 1. No star-splat unpacking in boolean ops
    if re.search(r'\.(union|cut|intersect)\(\s*\*', code):
        raise ValueError(
            "Star-splat unpacking in .union()/.cut()/.intersect() is invalid — "
            "second item maps to 'clean=' parameter, silently corrupts geometry. "
            "Use .union(partA).union(partB) chained calls instead."
        )

    # 2. No empty boolean calls
    for op in ('union', 'cut', 'intersect'):
        if re.search(rf'\.{op}\(\s*\)', code):
            raise ValueError(
                f"Empty .{op}() call with no argument — always crashes. "
                f"Either provide a solid to {op} with, or remove the call."
            )

    # 3. Non-existent rotation methods
    for meth in ('rotateAboutX', 'rotateAboutY', 'rotateAboutZ'):
        if meth in code:
            raise ValueError(
                f".{meth}() does not exist in CadQuery. "
                f"Use .rotate((x1,y1,z1),(x2,y2,z2), angle) or .rotateX/Y/Z() instead."
            )

    # 4. Lambda geometry factories (objects get discarded)
    if re.search(r'lambda\s+\w+\s*:\s*cq\.Workplane', code):
        raise ValueError(
            "Lambda geometry factories return discarded objects — nothing gets unioned. "
            "Use a regular function or list comprehension + union chain instead."
        )

    # 5. sum() list-union pattern
    if re.search(r'\bsum\s*\(\s*\[', code) and 'cq.Workplane' in code:
        raise ValueError(
            "sum(parts, cq.Workplane()) is an invalid list-union pattern. "
            "Use functools.reduce(lambda a,b: a.union(b), parts) instead."
        )

    # 6. .fillet() immediately after .union() (high BRep_API crash risk)
    if re.search(r'\.union\([^)]*\)\s*\.fillet\(', code):
        raise ValueError(
            ".fillet() called directly after .union() — high BRep_API crash risk. "
            "Complete all unions first, then apply filleting to the final result."
        )

    # 7. Forbidden imports (numpy, pyvista, etc. — not available in CQ environment)
    forbidden = ['numpy', 'pyvista', 'trimesh', 'vtk', 'FreeCAD', 'scipy', 'shapely', 'matplotlib']
    for lib in forbidden:
        if re.search(rf'\bimport\s+{lib}\b', code) or re.search(rf'\bfrom\s+{lib}\b', code):
            raise ValueError(
                f"'import {lib}' is not available in the CadQuery executor. "
                f"Only 'import cadquery as cq' and 'import math' are allowed."
            )

    # 8. Reversed cylinder() argument order heuristic
    # .cylinder(small_number, large_number) → likely radius-first (wrong)
    cyl_matches = re.findall(r'\.cylinder\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)', code)
    for h_arg, r_arg in cyl_matches:
        h, r = float(h_arg), float(r_arg)
        if h < 5 and r > 50:
            raise ValueError(
                f".cylinder({h_arg}, {r_arg}) looks like reversed args — "
                f"CadQuery cylinder() signature is (height, radius). "
                f"HEIGHT is first. Use .cylinder({r_arg}, {h_arg}) if {r_arg} was meant to be the height."
            )

    # 9. Bare unassigned geometry calls (geometry created but never stored)
    lines = code.split('\n')
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        # Check for standalone cq.Workplane(...) calls not assigned to anything
        if re.match(r'^cq\.Workplane\(', stripped) and not re.match(r'^\w+\s*=', stripped) and not stripped.startswith('#'):
            raise ValueError(
                f"Line {lineno}: Unassigned cq.Workplane() call — geometry is created then immediately discarded. "
                f"Always assign: 'my_part = cq.Workplane(...)'"
            )


def extract_params_from_response(raw_response: str) -> Optional[dict]:
    """
    Try to extract a params dict from an intent-extraction response.
    Returns None if no structured params found.
    """
    return extract_json_params(raw_response)


def extract_json_params(raw_response: str) -> Optional[dict]:
    """
    Robustly extract the first JSON object from an LLM response.
    Uses brace-matching to correctly handle nested JSON structures.
    Strips DeepSeek <think> blocks and markdown fences before parsing.
    """
    if not raw_response or not raw_response.strip():
        return None

    # Strip reasoning model <think> blocks
    cleaned = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()

    # Try ```json ... ``` block first
    json_fence = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
    if json_fence:
        try:
            return json.loads(json_fence.group(1))
        except json.JSONDecodeError:
            pass

    # Brace-matching: find the outermost { ... } and parse it
    start = cleaned.find('{')
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(cleaned[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def extract_spec_json(raw_response: str) -> Optional[dict]:
    """
    Extract the structured geometry spec JSON from an enhancer response.
    Looks for a SPEC_JSON: prefix followed by a JSON block.
    Falls back to generic JSON extraction if no prefix marker found.
    """
    if not raw_response:
        return None

    # Strip reasoning blocks
    cleaned = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()

    # Try SPEC_JSON: marker first
    spec_match = re.search(r'SPEC_JSON:\s*```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
    if spec_match:
        try:
            return json.loads(spec_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try SPEC_JSON: without fences
    spec_match2 = re.search(r'SPEC_JSON:\s*(\{.*?\})', cleaned, re.DOTALL)
    if spec_match2:
        try:
            return json.loads(spec_match2.group(1))
        except json.JSONDecodeError:
            pass

    # Fall back to finding any JSON object — use the largest one found
    # (the spec will generally be the biggest JSON in the response)
    candidates = []
    start = 0
    while True:
        idx = cleaned.find('{', start)
        if idx < 0:
            break
        depth = 0
        in_str = False
        esc = False
        for i, ch in enumerate(cleaned[idx:], idx):
            if esc:
                esc = False
                continue
            if ch == '\\' and in_str:
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(cleaned[idx:i + 1])
                        candidates.append((i - idx, obj))  # (length, parsed)
                    except json.JSONDecodeError:
                        pass
                    start = i + 1
                    break
        else:
            break

    if candidates:
        # Return the largest JSON object found
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return None
