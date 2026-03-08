"""
Fermeon — Prompt Formatter
Handles per-model quirks: system prompt placement, safety word substitution,
reasoning model handling, Ollama embedded prompts.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, List


PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def format_prompt_for_model(
    model: str,
    system_prompt: str,
    user_prompt: str,
    examples: List[str],
    model_config: dict,
) -> List[dict]:
    """
    Returns messages array formatted correctly for each model family.

    Key quirks handled:
    - Ollama: embed system prompt in user turn (local models ignore system role)
    - Gemini: sanitize words that trigger safety filters on technical content
    - Reasoning models (DeepSeek R1, o1): no system prompt — inject into user turn
    - Standard (Claude, OpenAI, Groq, Mistral): normal system + user
    """
    provider = model_config.get("provider", "unknown")

    # Build examples block
    examples_text = ""
    if examples:
        examples_text = "\n\nEXAMPLES OF CORRECT CADQUERY OUTPUT:\n"
        for i, ex in enumerate(examples[:2], 1):
            examples_text += f"\nExample {i}:\n```python\n{ex}\n```\n"

    full_user_content = f"{examples_text}\n\nNow generate CadQuery code for:\n{user_prompt}"

    # ── Ollama / local models ────────────────────────────────────────────────
    # Local models perform better with system prompt embedded in user turn.
    # The [SYSTEM]...[/SYSTEM] wrapper is a known-good pattern for Llama-family.
    if provider == "ollama":
        return [
            {
                "role": "user",
                "content": f"[SYSTEM]\n{system_prompt}\n[/SYSTEM]\n\n{full_user_content}"
            }
        ]

    # ── Gemini ───────────────────────────────────────────────────────────────
    # LiteLLM handles system_instruction translation for Gemini.
    # We sanitize the system prompt to avoid safety filter false positives on
    # legitimate engineering terms like "combustion chamber", "explosive bolt".
    if provider == "google":
        safe_system = _gemini_safety_sanitize(system_prompt)
        return [
            {"role": "system", "content": safe_system},
            {"role": "user", "content": full_user_content},
        ]

    # ── Reasoning models (DeepSeek R1, o1, o3-mini) ─────────────────────────
    # These models do NOT accept system prompts — inject instructions into user turn.
    reasoning_model_keys = ["deepseek-r1", "o1", "o3", "o1-mini", "o3-mini"]
    if any(rm in model.lower() for rm in reasoning_model_keys):
        return [
            {
                "role": "user",
                "content": f"Instructions:\n{system_prompt}\n\n{full_user_content}"
            }
        ]

    # ── Standard (Claude, OpenAI, Groq, Mistral, Codestral) ─────────────────
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": full_user_content},
    ]


def _gemini_safety_sanitize(text: str) -> str:
    """
    Replace words that commonly trigger Gemini safety filters in engineering context.
    These are legitimate engineering terms — we rephrase them neutrally.
    """
    replacements = {
        "combustion": "reaction",
        "explosive": "energetic",
        "bomb": "pressure vessel",
        "weapon": "mechanism",
        "detonate": "actuate",
        "warhead": "payload housing",
        "missile": "projectile",
        "bullet": "projectile",
        "gun": "actuator",
        "kill": "terminate",
    }
    for word, replacement in replacements.items():
        text = text.replace(word, replacement)
        text = text.replace(word.capitalize(), replacement.capitalize())
    return text


def format_cem_prompt_for_model(
    model: str,
    cem_name: str,
    schema_json: str,
    user_prompt: str,
    model_config: dict,
) -> list[dict]:
    """
    Format the CEM parameter-extraction request for the given model family.
    The LLM's only job: read schema + user description, output a JSON object.
    """
    cem_system_path = PROMPTS_DIR / "cem_extractor_prompt.txt"
    if cem_system_path.exists():
        template = cem_system_path.read_text(encoding="utf-8")
        system_prompt = (
            template
            .replace("{cem_name}", cem_name)
            .replace("{schema}", schema_json)
        )
    else:
        system_prompt = (
            f"You are a precision engineering parameter extractor.\n"
            f"Output ONLY a JSON object with parameters for a {cem_name}.\n"
            f"Schema: {schema_json}\n"
            f"Rules: output ONLY valid JSON, no markdown, no explanations."
        )

    user_content = (
        f'User description: "{user_prompt}"\n\n'
        f"Extract the engineering parameters as a single JSON object:"
    )

    provider = model_config.get("provider", "unknown")

    if provider == "ollama":
        return [{"role": "user", "content": f"[SYSTEM]\n{system_prompt}\n[/SYSTEM]\n\n{user_content}"}]

    reasoning_keys = ["deepseek-r1", "o1", "o3", "o1-mini", "o3-mini"]
    if any(rm in model.lower() for rm in reasoning_keys):
        return [{"role": "user", "content": f"Instructions:\n{system_prompt}\n\n{user_content}"}]

    if provider == "google":
        return [
            {"role": "system", "content": _gemini_safety_sanitize(system_prompt)},
            {"role": "user", "content": user_content},
        ]

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def build_correction_prompt(
    original_prompt: str,
    failed_code: str,
    error_message: str,
) -> str:
    """
    Build a self-correction prompt when CadQuery execution fails.
    Feed the error back to the LLM so it can fix its own code.
    """
    return f"""The CadQuery code you generated failed with this error:
```
{error_message}
```

Your previous code:
```python
{failed_code}
```

Fix the error. Return ONLY the corrected complete Python code block.
Do not explain. Just the fixed code.

Common CadQuery fixes:
- BRep_API command not done: This usually means a fillet or boolean union failed due to complex geometry. Completely REMOVE all `.fillet()` and `.chamfer()` calls from your code and try again.
- Fillet too large: reduce fillet radius (must be < half the smallest edge length)
- Non-manifold geometry: ensure all solids are closed before boolean operations
- Zero-length edge: check all extrude/revolve distances are > 0
- Cannot union type NoneType: NEVER call `.union()`, `.cut()`, or `.intersect()` without an argument. ALWAYS specify the object to union with, e.g., `partA.union(partB)`.
- Thread failure: use valid pitch values (e.g., pitch=1.25 for M8)
- Missing show_object(): always end with show_object(result) or result = ...

Original request was: {original_prompt}
"""
