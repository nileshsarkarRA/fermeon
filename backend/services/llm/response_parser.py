"""
Fermeon — Response Parser
Extracts Python/CadQuery code from LLM responses regardless of formatting.
Models wrap code in wildly different ways — this handles all of them.
"""

import re
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
    try:
        import json
        # Look for JSON block
        json_block = re.search(r'```json\s*(.*?)```', raw_response, re.DOTALL)
        if json_block:
            return json.loads(json_block.group(1).strip())

        # Look for bare JSON object
        obj_match = re.search(r'\{[^{}]*\}', raw_response, re.DOTALL)
        if obj_match:
            return json.loads(obj_match.group(0))
    except Exception:
        pass
    return None
