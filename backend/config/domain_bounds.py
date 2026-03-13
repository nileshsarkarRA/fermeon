"""
Fermeon — Domain Bounding-Box Bounds
Per-domain expected size ranges (mm) for post-execution sanity checks.
A generated model whose largest dimension falls outside [min, max] is
rejected — this catches scale failures that pass syntax/CQ validation.
"""

DOMAIN_BOUNDS: dict[str, dict[str, float]] = {
    "furniture":            {"min": 100.0,   "max": 4000.0},
    "architecture":         {"min": 50.0,    "max": 100_000.0},
    "aerospace":            {"min": 30.0,    "max": 60_000.0},
    "biomedical":           {"min": 2.0,     "max": 800.0},
    "industrial":           {"min": 10.0,    "max": 10_000.0},
    "marine":               {"min": 50.0,    "max": 50_000.0},
    "consumer_electronics": {"min": 5.0,     "max": 600.0},
    "organic":              {"min": 5.0,     "max": 5000.0},
    "mechanical":           {"min": 2.0,     "max": 2000.0},
    "automotive":           {"min": 10.0,    "max": 5000.0},
    "generic":              {"min": 0.5,     "max": 200_000.0},
}


def get_bounds(domain: str) -> dict[str, float]:
    """Return (min, max) mm bounds for a domain, falling back to generic."""
    return DOMAIN_BOUNDS.get(domain, DOMAIN_BOUNDS["generic"])
