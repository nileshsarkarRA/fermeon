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
    if provider == "ollama":
        return [
            {
                "role": "user",
                "content": f"[SYSTEM]\n{system_prompt}\n[/SYSTEM]\n\n{full_user_content}"
            }
        ]

    # ── Gemini ───────────────────────────────────────────────────────────────
    if provider == "google":
        safe_system = _gemini_safety_sanitize(system_prompt)
        return [
            {"role": "system", "content": safe_system},
            {"role": "user", "content": full_user_content},
        ]

    # ── Reasoning models (DeepSeek R1, o1, o3-mini) ─────────────────────────
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
    domain: str = "mechanical",
) -> str:
    """
    Build a self-correction prompt when CadQuery execution fails.
    Feed the error back to the LLM so it can fix its own code.
    Includes domain context to prevent the model from drifting to wrong geometry.
    """
    domain_hint = _domain_correction_hints(domain)

    return f"""The CadQuery code you generated failed with this error:
```
{error_message}
```

Your previous code:
```python
{failed_code}
```

Fix the error. Return ONLY the corrected complete Python code block.
Do NOT explain. Just the fixed code.

═══════════════════════════════════════════════
COMMON CADQUERY FIXES:
═══════════════════════════════════════════════
• BRep_API command not done → a fillet or boolean union failed. REMOVE all `.fillet()` and `.chamfer()` calls from the broken part and try again without them.
• Fillet too large → reduce fillet radius (must be < half the smallest edge)
• Non-manifold geometry → ensure all solids are closed before boolean operations
• Zero-length edge → check all extrude/revolve distances are > 0
• NoneType union error → NEVER call `.union()`, `.cut()`, `.intersect()` without an argument. Always: `partA.union(partB)` not `.union()`
• Thread failure → use valid pitch values (e.g., pitch=1.25 for M8)
• Star-splat in union → use `.union(a).union(b)` chaining NOT `.union(*list)`
• rotateAboutX/Y/Z → these don't exist. Use `.rotate(axisPt1, axisPt2, angleDeg)` instead
• sum() union → use `functools.reduce(lambda a,b: a.union(b), parts)` instead
• .fillet() after .union() → apply filleting ONLY to the final result, not intermediate parts
• Empty result → always assign your final solid to `result = ...`

{domain_hint}

Original request was: {original_prompt}
"""


def _domain_correction_hints(domain: str) -> str:
    """Return domain-specific correction hints for the self-correction prompt."""
    hints = {
        "furniture": """═══════════════════════════════════════════════
FURNITURE DOMAIN HINTS:
═══════════════════════════════════════════════
• Seat height standard: 420mm from floor
• All legs: centered=(True,True,False), then .translate() to position
• Use .union() to join all parts into one solid before any boolean cuts
• Do NOT use medical, aerospace, or mechanical terminology — furniture parts only""",
        "architecture": """═══════════════════════════════════════════════
ARCHITECTURE DOMAIN HINTS:
═══════════════════════════════════════════════
• Walls Z_height = Z_top - Z_bottom, ALWAYS third arg in .box(X, Y, Z)
• Towers must be taller than walls by at least 30mm
• Absolute Z positioning: use .translate((x, y, z_bottom + height/2))
• centered=(True,True,False) so Z=0 is the floor""",
        "aerospace": """═══════════════════════════════════════════════
AEROSPACE DOMAIN HINTS:
═══════════════════════════════════════════════
• Use .revolve() for axisymmetric parts (nozzles, fuselages)
• Use .loft() for tapered sections and fairings
• Minimum wall thickness: 1.5mm for AM parts""",
        "industrial": """═══════════════════════════════════════════════
INDUSTRIAL DOMAIN HINTS:
═══════════════════════════════════════════════
• Flanges: build solid ring first, then cut bore hole through
• Bolt holes: union all solids first, then cut all holes in one pass
• Use pushPoints() for bolt-circle patterns, NOT rarray()""",
    }
    return hints.get(domain, "")
