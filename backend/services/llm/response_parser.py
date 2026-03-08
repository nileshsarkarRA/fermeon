"""
Fermeon — Response Parser
Extracts Python/CadQuery code from LLM responses regardless of formatting.
Models wrap code in wildly different ways — this handles all of them.
"""

import ast
import ast
import re
import json
from typing import Optional


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
        if _looks_like_cadquery(code):
            return code

    # Pattern 2: ``` ... ``` (generic code block)
    generic_block = re.search(r'```(?:\w+)?\s*(.*?)```', raw_response, re.DOTALL)
    if generic_block:
        code = generic_block.group(1).strip()
        if _looks_like_cadquery(code):
            return code

    # Pattern 3: Raw code with no fences (some Ollama models emit bare code)
    if _looks_like_cadquery(raw_response):
        lines = raw_response.split('\n')
        code_start = next(
            (i for i, line in enumerate(lines)
             if line.strip().startswith(("import", "#", "params", "result", "cq."))),
            0
        )
        return '\n'.join(lines[code_start:]).strip()

    # Pattern 4: Code embedded in explanation — find the code section
    sections = raw_response.split('\n\n')
    for section in sections:
        if _looks_like_cadquery(section):
            return section.strip()

    # Pattern 5: Check if there's ANY python import block
    any_block = re.search(r'(import cadquery.*)', raw_response, re.DOTALL)
    if any_block:
        return any_block.group(1).strip()

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
    ]
    return any(marker in text for marker in cadquery_markers)


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


def validate_python_syntax(code: str) -> tuple[bool, str]:
    """
    Check whether a code string is valid Python using the AST parser.
    Returns (True, "") on success, (False, error_description) on failure.
    """
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as exc:
        return False, f"line {exc.lineno}: {exc.msg}"
    except Exception as exc:
        return False, str(exc)
