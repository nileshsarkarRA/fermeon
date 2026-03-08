"""
Fermeon — GPT-Powered CAD Domain Generator
Queries GPT-4o to produce a comprehensive, exhaustive list of ALL engineering/design
domains where CAD models are relevant. Merges results with existing cad_domains.json
so you can incrementally expand the list without duplicates.

Run:
    python generate_domains.py

Requires: pip install openai
Outputs : backend/cad_domains.json   (updated domain data)
          backend/services/domain_enricher.py reloads this automatically on next start
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from openai import OpenAI

# ── Config ─────────────────────────────────────────────────────────────────────
API_KEY   = os.getenv("OPENAI_API_KEY", "sk-YOUR_KEY_HERE")
MODEL     = "gpt-4o"
OUT_JSON  = Path(__file__).parent / "backend" / "cad_domains.json"
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a senior mechanical engineer and product architect with deep knowledge of
every industry that uses CAD (Computer-Aided Design) software.
Your job is to enumerate EVERY domain, sub-domain, and niche where physical objects
are designed using parametric or solid-modelling CAD tools.

Rules:
- Return ONLY a flat JSON array of strings.
- Each string is a domain or sub-domain name (max ~6 words).
- Be exhaustive: include mainstream AND obscure/niche industries.
- No descriptions, no explanations, no markdown — pure JSON array only.
- Aim for at least 300 distinct entries covering the full breadth of engineering,
  architecture, consumer products, medical, aerospace, marine, automotive,
  jewellery, electronics, agriculture, defence, sports, furniture, toys, etc.
"""

USER_PROMPT = """
Generate the most comprehensive possible flat list of ALL domains where CAD models
are created and used. Cover every industry, sub-industry, and niche you can think of.
Output must be a raw JSON array of domain name strings only. Nothing else.
"""


def fetch_domains(client: OpenAI) -> list[str]:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_PROMPT},
        ],
        temperature=0.7,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return parsed
    for v in parsed.values():
        if isinstance(v, list):
            return v
    raise ValueError(f"Unexpected JSON shape: {raw[:200]}")


def load_existing(path: Path) -> list[str]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def dedupe_merge(existing: list[str], new: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for d in existing + new:
        key = d.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(d.strip())
    return sorted(result, key=str.lower)


def save_json(domains: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(domains, f, indent=2, ensure_ascii=False)
    print(f"  → {path}  ({len(domains)} domains total)")


def main() -> None:
    print("Fermeon Domain Generator")
    print("=" * 40)
    print(f"Model  : {MODEL}")
    print(f"Output : {OUT_JSON}")
    print()

    if API_KEY == "sk-YOUR_KEY_HERE":
        print("ERROR: Set OPENAI_API_KEY environment variable before running.")
        print("  $env:OPENAI_API_KEY = 'sk-...'  (PowerShell)")
        print("  export OPENAI_API_KEY='sk-...'   (bash)")
        return

    existing = load_existing(OUT_JSON)
    print(f"Existing domains: {len(existing)}")

    client = OpenAI(api_key=API_KEY)

    print("Querying GPT-4o …")
    raw_domains = fetch_domains(client)
    print(f"  Raw entries returned : {len(raw_domains)}")

    merged = dedupe_merge(existing, raw_domains)
    added  = len(merged) - len(existing)
    print(f"  New unique entries   : {added}")
    print(f"  Total after merge    : {len(merged)}")
    print()

    save_json(merged, OUT_JSON)

    print()
    print("Sample (first 20):")
    for d in merged[:20]:
        print(f"  • {d}")
    if len(merged) > 20:
        print(f"  … and {len(merged) - 20} more")

    print()
    print("Done. Restart the Fermeon backend to pick up the new domains.")


if __name__ == "__main__":
    main()
