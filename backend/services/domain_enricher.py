"""
Fermeon — Domain-Aware Prompt Enricher
Loads cad_domains.json and injects relevant domain context into CAD generation
prompts before they are sent to the LLM, significantly improving output quality.
"""

from __future__ import annotations

import json
import random
from difflib import get_close_matches
from pathlib import Path
from typing import Tuple, List, Dict, Type, Optional

_DOMAINS_FILE = Path(__file__).parent.parent / "cad_domains.json"

# ── Loader ─────────────────────────────────────────────────────────────────────

def _load_domains(path: Path = _DOMAINS_FILE) -> List[str]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


DOMAINS: List[str] = _load_domains()

# Pre-build a lowercase lookup list for fast searching
_DOMAINS_LOWER: List[str] = [d.lower() for d in DOMAINS]

# Common words to ignore during word-level search (too generic to be useful)
_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or",
    "with", "by", "from", "up", "as", "is", "it", "its",
})


# ── Core Search ────────────────────────────────────────────────────────────────

def _score_domain(query_words: List[str], domain_lower: str) -> int:
    """
    Return a relevance score for a domain string vs the query word list.
    Higher = more relevant.  Multi-word phrase hits score higher.
    """
    score = 0
    domain_words = set(domain_lower.split())
    for w in query_words:
        if w in domain_lower:
            # Bonus for whole-word match
            score += 3 if w in domain_words else 1
    return score


def search_domains(query: str, n: int = 10) -> List[str]:
    """
    Return the top-n domain names most relevant to *query*.
    Combines scored substring matching (exact) with fuzzy matching (typo-tolerant).
    """
    q = query.lower()

    # Extract meaningful words (5+ chars, not stop words)
    sig_words = [w for w in q.split() if len(w) >= 5 and w not in _STOP_WORDS]
    # Also include 4-char words for short technical terms (gear, pump, bolt, etc.)
    all_words = [w for w in q.split() if len(w) >= 4 and w not in _STOP_WORDS]

    # Phase 1: full-phrase substring match (highest precision)
    phrase_hits: List[Tuple[int, str]] = []
    for i, d in enumerate(_DOMAINS_LOWER):
        if q in d:
            phrase_hits.append((_score_domain(all_words, d), DOMAINS[i]))

    # Phase 2: significant-word scoring (4+ char words to catch "sofa", "gear", etc.)
    word_hits: List[Tuple[int, str]] = []
    phrase_set = {h[1] for h in phrase_hits}
    for i, d in enumerate(_DOMAINS_LOWER):
        dom = DOMAINS[i]
        if dom in phrase_set:
            continue
        score = _score_domain(all_words, d)
        if score > 0:
            word_hits.append((score, dom))

    # Phase 3: fuzzy fallback for typos / synonyms
    fuzzy = get_close_matches(query, DOMAINS, n=n, cutoff=0.4)

    # Sort by score descending, then merge
    phrase_hits.sort(key=lambda x: -x[0])
    word_hits.sort(key=lambda x: -x[0])

    seen: set[str] = set()
    combined: List[str] = []
    for _, dom in phrase_hits + word_hits:
        if dom not in seen:
            seen.add(dom)
            combined.append(dom)
    for dom in fuzzy:
        if dom not in seen:
            seen.add(dom)
            combined.append(dom)

    return combined[:n]


def random_domains(n: int = 8) -> List[str]:
    """Return n randomly sampled domain names (for UI suggestion chips)."""
    return random.sample(DOMAINS, min(n, len(DOMAINS)))


# ── Prompt Enrichment ──────────────────────────────────────────────────────────

def enrich_prompt(user_prompt: str, domain: str = "") -> str:
    """
    Prepend a short domain-context hint to the user prompt so the LLM
    understands which engineering domain is being targeted.

    Parameters
    ----------
    user_prompt : str
        The enhanced user prompt from LLM trip 1.
    domain : str
        Optional: already-detected domain (e.g. 'furniture') to bias the search.

    Example
    -------
    user_prompt  = "design a hip replacement implant"
    → "[Domain: Orthopaedic Hip Implants / Prosthetic Limb Sockets]\ndesign a hip replacement implant"
    """
    # Bias the search with the known domain string if provided
    search_text = f"{domain} {user_prompt}" if domain else user_prompt
    matches = search_domains(search_text, n=3)
    if not matches:
        return user_prompt
    domain_hint = " / ".join(matches[:2])
    return f"[Domain: {domain_hint}]\n{user_prompt}"


def domain_system_fragment(user_prompt: str, n: int = 5) -> str:
    """
    Build a short system-prompt fragment naming the relevant domain(s).
    Inject this into the CadQuery system prompt for higher accuracy.

    Returns an empty string when no relevant domains are found.
    """
    matches = search_domains(user_prompt, n=n)
    if not matches:
        return ""
    joined = ", ".join(matches[:3])
    return (
        f"The user is working in the following CAD domain(s): {joined}. "
        "Apply domain-appropriate design conventions, realistic proportions, "
        "standard tolerances, and part naming conventions in the generated CadQuery code."
    )


# ── Utility ────────────────────────────────────────────────────────────────────

def list_all() -> List[str]:
    """Return the full domain list (read-only copy)."""
    return list(DOMAINS)


def total() -> int:
    """Return total number of loaded domains."""
    return len(DOMAINS)


# ── CLI demo ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Loaded {total()} CAD domains.\n")

    examples = [
        "hip replacement implant",
        "drone propeller",
        "wristwatch case",
        "bridge truss",
        "circuit board enclosure",
        "racing car suspension arm",
        "greenhouse bracket",
        "acoustic guitar body",
        "turbine blade",
        "prosthetic hand mechanism",
    ]

    for ex in examples:
        enriched = enrich_prompt(ex)
        sysfrag = domain_system_fragment(ex)
        print(f"Prompt   : {ex}")
        print(f"Enriched : {enriched}")
        print(f"SysFrag  : {sysfrag}")
        print()
