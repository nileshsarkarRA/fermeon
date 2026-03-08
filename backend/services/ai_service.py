"""
Fermeon — AI Service
Handles system prompt building, example loading, and intent extraction.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def build_system_prompt(domain: str = "mechanical") -> str:
    """
    Build the system prompt for CadQuery code generation.
    Combines the base system prompt with domain-specific context.
    """
    # Load base prompt
    base_path = PROMPTS_DIR / "system_prompt.txt"
    try:
        base_prompt = base_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        base_prompt = _default_system_prompt()

    # Load domain-specific additions
    domain_path = PROMPTS_DIR / "domain_prompts" / f"{domain}.txt"
    domain_context = ""
    if domain_path.exists():
        domain_context = f"\n\nDOMAIN CONTEXT ({domain.upper()}):\n{domain_path.read_text(encoding='utf-8')}"

    return f"{base_prompt}{domain_context}"


def load_examples(part_type: str = "generic") -> list[str]:
    """
    Load few-shot CadQuery examples for the given part type.
    Falls back to generic examples if no specific ones found.
    """
    examples_dir = PROMPTS_DIR / "examples"
    examples = []

    # Try part-specific example first
    specific = examples_dir / f"{part_type}.py"
    if specific.exists():
        examples.append(specific.read_text(encoding="utf-8"))

    # Always include a generic bracket example
    bracket = examples_dir / "bracket.py"
    if bracket.exists() and str(bracket) != str(specific):
        examples.append(bracket.read_text(encoding="utf-8"))

    return examples[:2]  # Max 2 examples to save tokens


def extract_intent(prompt: str, model: str = None) -> dict:
    """
    Parse user prompt to extract key intent signals.
    This is a lightweight local extraction — no LLM call needed for basic cases.
    For complex assemblies, the generate endpoint can call this with the model.
    """
    prompt_lower = prompt.lower()

    # Part type detection
    part_type = "generic"
    part_map = {
        "bracket": "bracket",
        "gear": "gear",
        "nozzle": "nozzle",
        "enclosure": "enclosure",
        "box": "enclosure",
        "housing": "enclosure",
        "bolt": "fastener",
        "screw": "fastener",
        "nut": "fastener",
        "washer": "fastener",
        "pipe": "pipe",
        "tube": "pipe",
        "shaft": "shaft",
        "plate": "plate",
        "flange": "flange",
        "spring": "spring",
        "bearing": "bearing",
    }
    for keyword, ptype in part_map.items():
        if keyword in prompt_lower:
            part_type = ptype
            break

    # Domain detection
    domain = "mechanical"
    domain_map = {
        "aerospace": ["aircraft", "aerospace", "fuselage", "wing", "rocket", "thrust", "nozzle"],
        "architecture": ["building", "column", "beam", "slab", "floor", "wall", "architectural"],
        "biomedical": ["implant", "prosthetic", "bone", "surgical", "medical", "orthopedic"],
        "mechanical": [],  # Default
    }
    for dom, keywords in domain_map.items():
        if any(kw in prompt_lower for kw in keywords):
            domain = dom
            break

    # Dimension extraction (simple regex for mm values)
    dimensions = {}
    dim_patterns = [
        (r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)(?:\s*mm)?', ["length", "width", "height"]),
        (r'(\d+(?:\.\d+)?)\s*mm\s+(?:diameter|dia|OD)', ["diameter"]),
        (r'(\d+(?:\.\d+)?)\s*mm\s+(?:thick|thickness)', ["thickness"]),
        (r'(\d+(?:\.\d+)?)\s*mm\s+(?:long|length)', ["length"]),
        (r'(\d+(?:\.\d+)?)\s*mm\s+(?:wide|width)', ["width"]),
        (r'(\d+(?:\.\d+)?)\s*mm\s+(?:tall|height)', ["height"]),
    ]

    for pattern, keys in dim_patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            for i, key in enumerate(keys):
                if i < len(match.groups()):
                    try:
                        dimensions[key] = float(match.group(i + 1))
                    except (ValueError, IndexError):
                        pass

    # Ambiguity detection (things that might need assumptions)
    ambiguities = []
    if "hole" in prompt_lower and "thread" not in prompt_lower:
        ambiguities.append("Hole threading not specified — assuming clearance hole")
    if "fillet" not in prompt_lower and "chamfer" not in prompt_lower:
        ambiguities.append("Edge treatment not specified — using small default fillets")
    if not dimensions:
        ambiguities.append("No dimensions specified — using standard proportions")

    return {
        "part_type": part_type,
        "domain": domain,
        "dimensions": dimensions,
        "ambiguities": ambiguities,
    }


def _default_system_prompt() -> str:
    """Fallback system prompt if file not found."""
    return """You are an expert CadQuery engineer specializing in parametric 3D CAD modeling.

Your task is to generate correct, production-ready CadQuery Python code for the described part.

RULES:
1. Always import cadquery as cq
2. Assign your final geometry to a variable named 'result'
3. Use millimeters for all dimensions unless explicitly stated otherwise
4. Use parameters (variables) for all key dimensions — never hardcode magic numbers
5. Ensure all geometry is valid and watertight (closed solids)
6. Use fillets and chamfers where engineering practice requires them
7. Write clean, commented code
8. Return ONLY the Python code — no explanations, no markdown, just the code block

CADQUERY BEST PRACTICES:
- Use cq.Workplane('XY').box() for rectangular solids
- Use .circle().extrude() for cylinders  
- Use .union(), .cut(), .intersect() for boolean operations
- Keep fillet radius < half the smallest wall thickness
- For holes: use .hole(diameter) for simple bores
- For threads: document the thread spec in comments

EXAMPLE STRUCTURE:
```python
import cadquery as cq

# Parameters
length = 100  # mm
width = 50    # mm  
height = 10   # mm

# Build geometry
result = (
    cq.Workplane("XY")
    .box(length, width, height)
    .edges("|Z").fillet(2)
)
```"""
