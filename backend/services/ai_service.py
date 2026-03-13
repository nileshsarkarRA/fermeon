"""
Fermeon — AI Service
Handles system prompt building, example loading, and intent extraction.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional, List

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Maps domain → ordered list of example file stems to try (best first)
_DOMAIN_TO_EXAMPLES: dict[str, list[str]] = {
    "furniture":            ["chair", "table", "sofa", "furniture"],
    "architecture":         ["building", "architecture"],
    "aerospace":            ["wing_section", "nozzle"],
    "biomedical":           ["pressure_flange", "vessel"],
    "industrial":           ["pressure_flange", "vessel"],
    "marine":               ["vessel"],
    "consumer_electronics": ["enclosure"],
    "organic":              ["mug", "sphere"],
    "mechanical":           ["bracket", "gear"],
    "automotive":           ["bracket"],
    "generic":              ["bracket"],
}

# Part-type → example file stem overrides (always tried first)
_PART_TYPE_TO_EXAMPLE: dict[str, str] = {
    "furniture":       "chair",
    "chair":           "chair",
    "table":           "table",
    "sofa":            "sofa",
    "bracket":         "bracket",
    "gear":            "gear",
    "nozzle":          "nozzle",
    "enclosure":       "enclosure",
    "fastener":        "bracket",
    "pipe":            "vessel",
    "flange":          "pressure_flange",
    "vessel":          "vessel",
    "wing_section":    "wing_section",
    "architecture":    "building",
    "building":        "building",
    "handheld_device": "enclosure",
    "mug":             "mug",
    "bowl":            "mug",
    "vase":            "mug",
}


def build_system_prompt(domain: str = "mechanical") -> str:
    """
    Build the system prompt for CadQuery code generation.
    Combines the base system prompt with domain-specific context.
    """
    base_path = PROMPTS_DIR / "system_prompt.txt"
    try:
        base_prompt = base_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        base_prompt = _default_system_prompt()

    # Load domain-specific additions
    domain_path = PROMPTS_DIR / "domain_prompts" / f"{domain}.txt"
    domain_context = ""
    if domain_path.exists():
        domain_context = (
            f"\n\nDOMAIN CONTEXT ({domain.upper()}):\n"
            f"{domain_path.read_text(encoding='utf-8')}"
        )

    return f"{base_prompt}{domain_context}"


def load_examples(part_type: str = "generic", domain: str = "") -> List[str]:
    """
    Load few-shot CadQuery examples for the given part type and domain.

    Priority:
      1. Part-type specific override (e.g. 'gear' → gear.py)
      2. Domain-ordered example list (e.g. 'furniture' → sofa.py, chair.py)
      3. Generic bracket.py as hard fallback

    Always returns at most 2 examples to save tokens.
    """
    examples_dir = PROMPTS_DIR / "examples"
    found: list[str] = []

    def _load(stem: str) -> Optional[str]:
        p = examples_dir / f"{stem}.py"
        return p.read_text(encoding="utf-8") if p.exists() else None

    # 1. Part-type specific
    specific_stem = _PART_TYPE_TO_EXAMPLE.get(part_type)
    if specific_stem:
        content = _load(specific_stem)
        if content:
            found.append(content)

    # 2. Domain-ordered fallbacks
    domain_key = domain if domain in _DOMAIN_TO_EXAMPLES else part_type
    for stem in _DOMAIN_TO_EXAMPLES.get(domain_key, []):
        if len(found) >= 1:   # 1 example max — saves tokens for richer spec
            break
        content = _load(stem)
        if content and content not in found:
            found.append(content)

    # 3. Hard fallback — bracket.py works for almost any mechanical prompt
    if not found:
        content = _load("bracket")
        if content:
            found.append(content)

    return found[:1]   # 1 example max


def extract_intent(prompt: str, model: str = None) -> dict:
    """
    Parse user prompt to extract key intent signals.
    Lightweight local extraction — no LLM call needed for basic cases.
    """
    prompt_lower = prompt.lower()

    # Part type detection — order matters (more specific first)
    part_type = "generic"
    part_map = {
        "bracket":    "bracket",
        "gear":       "gear",
        "nozzle":     "nozzle",
        "enclosure":  "enclosure",
        "box":        "enclosure",
        "housing":    "enclosure",
        "bolt":       "fastener",
        "screw":      "fastener",
        "nut":        "fastener",
        "washer":     "fastener",
        "pipe":       "pipe",
        "tube":       "pipe",
        "shaft":      "shaft",
        "plate":      "plate",
        "flange":     "flange",
        "spring":     "spring",
        "bearing":    "bearing",
        "vessel":     "vessel",
        "tank":       "vessel",
        "chair":      "furniture",
        "table":      "furniture",
        "desk":       "furniture",
        "sofa":       "furniture",
        "couch":      "furniture",
        "shelf":      "furniture",
        "cabinet":    "furniture",
        "bed":        "furniture",
        "furniture":  "furniture",
        "castle":     "architecture",
        "building":   "architecture",
        "tower":      "architecture",
        "bridge":     "architecture",
        "wall":       "architecture",
        "arch":       "architecture",
        "wing":       "wing_section",
        "airfoil":    "wing_section",
        "ipod":       "handheld_device",
        "iphone":     "handheld_device",
        "phone":      "handheld_device",
        "smartphone": "handheld_device",
        "tablet":     "handheld_device",
        "ipad":       "handheld_device",
        "phablet":    "handheld_device",
        "handheld":   "handheld_device",
    }
    for keyword, ptype in part_map.items():
        if keyword in prompt_lower:
            part_type = ptype
            break

    # Domain detection
    domain = "mechanical"
    domain_map = {
        "aerospace":            ["aircraft", "aerospace", "fuselage", "wing", "rocket", "thrust", "nozzle", "airfoil", "drone"],
        "architecture":         ["building", "column", "beam", "slab", "floor", "wall", "architectural", "castle", "house", "fort", "bridge", "tower", "arch"],
        "biomedical":           ["implant", "prosthetic", "bone", "surgical", "medical", "orthopedic", "prosthesis"],
        "consumer_electronics": ["ipod", "iphone", "phone", "smartphone", "tablet", "ipad", "handheld", "device", "gadget", "electronics", "pcb", "circuit"],
        "furniture":            ["chair", "table", "desk", "seat", "sofa", "couch", "bed", "furniture", "cabinet", "shelf", "armrest", "ottoman", "bench"],
        "industrial":           ["valve", "flange", "pipe", "pressure", "vessel", "tank", "pump", "compressor"],
        "marine":               ["hull", "propeller", "keel", "boat", "ship", "submarine", "underwater"],
        "organic":              ["organic", "generative", "leap 71", "cadam", "formless", "topology", "smooth", "fluid", "sculpted", "vase", "sculpture"],
        "automotive":           ["car", "vehicle", "chassis", "engine", "wheel", "bumper", "hood", "automotive"],
        "mechanical":           [],  # Default
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

    # Ambiguity detection
    ambiguities = []
    if "hole" in prompt_lower and "thread" not in prompt_lower:
        ambiguities.append("Hole threading not specified — assuming clearance hole")
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
- ALWAYS use centered=(True, True, False) for floor-resting geometry
- ALWAYS use .translate((x, y, z)) to position parts with Z-stacking

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
