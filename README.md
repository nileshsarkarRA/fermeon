# Fermeon — AI CAD Generator

Fermeon converts natural language into production-ready CAD files (STEP + STL) using a multi-LLM pipeline built on CadQuery and FastAPI. Describe any part in plain English; Fermeon writes, validates, and self-corrects the parametric Python code until valid geometry is produced.

---

## Features

- **7-step generation pipeline** — Intent extraction → domain enrichment → LLM prompt enhancement (Trip 1) → LLM code generation (Trip 2-N) → non-Python stripping + import repair → Python syntax check → CadQuery execution. Each failure stage carries the exact error message and broken code into the next attempt so corrections are targeted, not blind.
- **Multi-LLM with automatic fallback** — Choose from 13 models across 6 providers. If a model fails or has no API key, Fermeon automatically falls back through the default chain.
- **Unified 3-attempt self-correction cap** — All failure modes (syntax error, wrong API, CadQuery crash) share the same 3-attempt budget. Each retry feeds the exact error back to the LLM as the correction prompt.
- **942-domain engineering knowledge base** — Prompts are matched against 942 engineering domains (Aerospace → Textile → Space Systems) to inject domain-specific context and vocabulary into both generation stages.
- **Automatic import repair** — If the LLM writes `from cadquery import Workplane, Box, ...` (invalid), Fermeon silently rewrites it to `import cadquery as cq` and prefixes all bare class names (`Workplane(` → `cq.Workplane(`). Capitalization typos (`cq.WorkPlane`) are also fixed unconditionally.
- **Python syntax validation** — `ast.parse` is run on every extracted code block before it reaches the CadQuery executor. A syntax error triggers an immediate targeted correction call instead of a silent crash.
- **Live token streaming** — Token count and elapsed time are printed to the server terminal in real time (every 20 tokens) so you can see generation progress without waiting for the full response.
- **Escalating local-model timeouts** — Ollama attempts are given 250 s → 350 s → 450 s. If attempt 1 finishes in 40 s, the result is used immediately; the larger budgets only apply if the earlier attempt actually timed out.
- **Interactive 3D preview** — Three.js WebGL viewer with orbit/pan/zoom directly in the browser. No plugins required.
- **Instant STEP + STL export** — Downloads available immediately after each successful generation.
- **Full session logs** — Every request is logged to `backend/logs/` as JSON including the final generated code, all retry history, token counts, cost estimate, and detected domain.
- **Black-theme settings panel** — Slide-out drawer groups models by type (Local / Cloud API) with live availability indicators, API key storage, domain selector, and generation toggles.
- **API keys stored locally only** — Keys are saved in browser `localStorage`, never sent to any server except the target LLM provider.

---

## Quick Start

```bat
# Windows
start.bat

# PowerShell
./start.ps1
```

The launcher: installs pip dependencies if missing → starts Ollama if installed → starts the FastAPI backend on port 8000 → opens the browser at `http://localhost:8000`.

---

## Supported Models

### Local (Ollama — free, runs on your GPU/CPU)

| Model | Display Name | Context | Best For |
|---|---|---|---|
| `ollama/codellama:7b` | CodeLlama 7B | 16k | Simple parts, learning |
| `ollama/codellama:13b` | CodeLlama 13B | 16k | Medium complexity |
| `ollama/deepseek-coder:6.7b` | DeepSeek Coder 6.7B | 16k | Fast iteration |
| `ollama/qwen2.5:7b` | Qwen2.5 7B | 32k | Complex parts, best local option |

Pull a model: `ollama pull qwen2.5:7b`

Local models are given **escalating timeouts** across the three internal LiteLLM attempts:

| LiteLLM attempt | Timeout |
|---|---|
| 1 | 250 s |
| 2 | 350 s |
| 3 | 450 s |

If attempt 1 finishes in 40 s, the result is used immediately — the larger budgets only apply if the prior attempt actually timed out. Generation progress (token count + elapsed time) is streamed to the server terminal in real time.

### Cloud API

| Model | Provider | Cost/1k tokens | Best For | Env Key |
|---|---|---|---|---|
| `gemini/gemini-2.0-flash` | Google | $0.000075 | Fast, cheap, large context | `GEMINI_API_KEY` |
| `gemini/gemini-2.5-pro` | Google | $0.00125 | Complex assemblies | `GEMINI_API_KEY` |
| `claude-sonnet-4-5` | Anthropic | $0.003 | Engineering accuracy | `ANTHROPIC_API_KEY` |
| `claude-haiku-4-5` | Anthropic | $0.00025 | Fast, cheap | `ANTHROPIC_API_KEY` |
| `gpt-4o` | OpenAI | $0.005 | General purpose | `OPENAI_API_KEY` |
| `gpt-4o-mini` | OpenAI | $0.000150 | Fast, cheap | `OPENAI_API_KEY` |
| `groq/llama-3.1-70b-versatile` | Groq | $0.00059 | Fast open-weights | `GROQ_API_KEY` |
| `groq/deepseek-r1-distill-llama-70b` | Groq | $0.00075 | Reasoning-heavy geometry | `GROQ_API_KEY` |
| `mistral/codestral-latest` | Mistral | $0.001 | Code specialist | `MISTRAL_API_KEY` |

Set environment variables or enter keys in the Settings panel. The **default fallback chain** is: `gemini-2.0-flash → llama-3.1-70b (Groq) → qwen2.5:7b (local)`.

> **Fallback bail-out rule:** If a model produces code that fails static validation (wrong API usage), Fermeon exits the fallback chain immediately and enters the self-correction loop with that model rather than trying a fresh model from scratch. A targeted correction is more effective than starting over.

---

## Architecture

```
USER PROMPT
     │
     ▼
[Pre-loop — runs once, no LLM]
  extract_intent()              local keyword scan → domain + part_type
  build_system_prompt()         loads domain txt + few-shot examples (sofa.py, chair.py…)
  domain_enrich_prompt()        injects domain vocabulary into prompt text
     │
     ▼ LLM TRIP 1  (optional — enhance_prompt toggle)
  gateway.enhance_prompt()      "a sofa" → full geometric spec with Z-stack + dimensions
     │                          also returns detected_domain; guarded: a model's
     │                          generic "mechanical" fallback cannot override a
     │                          domain that was already correctly identified by intent.
     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  RETRY LOOP  (max 3 attempts — ALL failure modes share the same cap)     │
│                                                                          │
│  ▼ LLM TRIP 2 (attempt 0) / TRIP 3-N (attempts 1+)                      │
│  attempt 0 : generate_cad_code()   enhanced prompt + examples            │
│  attempt 1+: self_correct()        failed_code + exact error → LLM       │
│                         ↑ the broken code is preserved so the model      │
│                           always sees what it wrote and why it failed     │
│                                                                          │
│  ▼ STRIP  (not a LLM call — response_parser.py)                         │
│  extract_code_from_response()      strips markdown fences, prose, show() │
│  _auto_fix_cq_imports()            rewrites bad import styles silently   │
│  _auto_alias_result()              adds `result = …` if missing          │
│  on failure: raw response saved so next self_correct has context         │
│                                                                          │
│  ▼ PYTHON CHECK  (not a LLM call)                                        │
│  ast.parse()                       full syntax check                     │
│  _validate_code_safety()           CadQuery-specific rule checks:        │
│    • wrong library / forbidden import                                    │
│    • cylinder(dia, …) arg order swapped                                  │
│    • box(height_var, …) axis confusion                                   │
│    • .union(*list) star-splat unpacking                                  │
│    • medical terminology in furniture code (domain confusion)            │
│    • lambda geometry factories                                           │
│    • .rotateAboutX/Y/Z() (non-existent methods)                          │
│    • empty .union()/.cut()/.intersect() calls                            │
│    • .fillet() after .union() (crash risk)                               │
│  on failure → last_error set; self_correct called with exact message     │
│                                                                          │
│  ▼ CADQUERY EXECUTE                                                      │
│  execute_cadquery_safe()           sandboxed subprocess, STEP + STL out  │
│  on failure → last_error set; continue                                   │
│  on success → BREAK ✓                                                    │
└──────────────────────────────────────────────────────────────────────────┘
     │
     ├── All 3 failed → HTTP 422 "Could not generate valid geometry after 3 attempt(s)"
     │
     ▼
  validate_mesh()               watertightness check on STL
  build file URLs               /files/<job_id>.step  +  .stl
  write_session_log()           JSON to backend/logs/<job_id>.json
  → GenerateResponse
```

### Key directories

```
backend/
  config/models.py          — model registry (add a model here, nothing else needed)
  routers/generate.py       — main pipeline endpoint (5-step loop)
  services/
    ai_service.py           — intent extraction, example loading, system prompt builder
    cad_executor.py         — sandboxed subprocess executor
    domain_enricher.py      — 942-domain search and context injection
    session_logger.py       — per-request JSON logs (code, tokens, cost, retries)
    llm/
      gateway.py            — LiteLLM wrapper, streaming, fallback chain, retries
      response_parser.py    — code extraction, import repair, syntax validation
      prompt_formatter.py   — few-shot example formatting, correction prompt builder
  prompts/
    system_prompt.txt       — code-gen rules (axis conventions, checklist, import rules)
    enhancer_prompt.txt     — spec-writer rules (Z-stacking, dimensions)
    examples/               — per-domain few-shot CadQuery examples
    domain_prompts/         — domain-specific system prompt fragments
    model_overrides/        — per-model addenda (Ollama, Gemini, GPT, reasoning models)
  cad_domains.json          — 942 engineering domains (generated, do not edit by hand)
frontend/
  index.html / app.js / styles.css   — single-page app, no build step
```

---

## Generation Pipeline Detail

### Trip 1 — Prompt Enhancement
The enhancer LLM rewrites a short prompt into a full geometric specification with explicit Z-stack, per-component footprints, `box(X=…, Y=…, Z=…)` labels, and Z_bottom/Z_top for every part. This prevents the most common failure modes: wrong axis assignment and floating disconnected geometry. Togglable per request; always recommended.

The enhancer also returns a `detected_domain` field. This is used to switch the system prompt and examples to a more specific domain (e.g. `furniture` instead of `mechanical`). A safety guard prevents a model's generic `"mechanical"` fallback from downgrading a domain that was already correctly identified by local intent extraction — for example, `qwen2.5:7b` misclassifying "a sofa" as mechanical.

### Trips 2-N — Code Generation + Self-Correction
Attempt 0 calls `generate_cad_code()` with the enhanced prompt, domain system prompt, and few-shot examples. Attempts 1+ call `self_correct()` which sends:
- The **broken code** from the previous attempt (not empty — preserved even on strip failure)
- The **exact error message** from whichever step failed (strip, syntax, or CadQuery)

The system prompt enforces:
- `import cadquery as cq` — the only valid import style
- `box(X_length, Y_width, Z_height)` — third argument is always vertical (Z)
- `cylinder(height, radius)` — height first, radius second
- `centered=(True, True, False)` for all floor-resting geometry
- `.translate((0, 0, z))` for exact Z-stacking
- Assembly Connectivity Law — every part's Z_min equals the part below's Z_max exactly
- Domain Coherence Law — only domain-appropriate part names (no medical device names on furniture)
- No `.fillet()` on complex union geometry (BRep_API crash risk)
- No invalid methods (`rotateAboutX`, `.copy()`, `.show()`, etc.)

### Strip — Automatic Code Repair (`response_parser.py`)
Applied silently before the syntax check:

| Issue | Fix |
|---|---|
| `from cadquery import Workplane, Box, …` | Removed; `import cadquery as cq` inserted at top |
| Bare `Workplane(` / `Assembly(` / `Vector(` | Prefixed with `cq.` |
| `cq.WorkPlane(` (wrong capitalisation) | Corrected to `cq.Workplane(` |
| `.show()` / `show_object()` / `display()` | Stripped (Jupyter-only calls) |
| `cq.exporters.export(result, "…")` | Stripped (executor handles exports) |
| No `result = …` assignment | `result = <last_workplane_var>` appended automatically |

### Python Check — `ast.parse` + `_validate_code_safety()`
Runs after the strip, before the CadQuery executor. Two phases:

**1. Syntax check** — `ast.parse` finds the exact line and message of any `SyntaxError`. That becomes the correction prompt so the LLM knows the line number, not just "the code is broken".

**2. Static safety validation** — `_validate_code_safety()` raises `ValueError` on patterns that always crash or produce wrong geometry:

| Pattern caught | Error message fed to next attempt |
|---|---|
| `box(height_var, …)` | Height variable as X (first) arg — must be third |
| `cylinder(dia_var, …)` or `cylinder(radius_var, …)` | Diameter/radius as first arg — HEIGHT must be first |
| `.union(*list_var)` / `.cut(*list_var)` | Star-splat unpacking — second item maps to `clean=` param, silently corrupts geometry |
| Medical terms (`spinal_fusion_cage`, `implant`, `vertebra`) in furniture code | Domain confusion — use furniture part names only |
| `lambda x: cq.Workplane(…)` factories | Lambdas return discarded objects; nothing is unioned |
| `.rotateAboutX/Y/Z()` | Non-existent CadQuery methods |
| `.union()` / `.cut()` with no argument | Empty boolean operation |
| `.fillet()` after `.union()` | High BRep_API crash risk |
| `sum(parts, cq.Workplane())` | Invalid list-union pattern |

Every `ValueError` from this step becomes the `last_error` fed into `self_correct()` for the next attempt — the model receives the exact rule it violated with correct/incorrect examples.

---

## Session Logs

Every request writes a JSON file to `backend/logs/<job_id>.json` containing:

```json
{
  "job_id": "41f75f5c-dd3",
  "prompt": "a sofa",
  "enhanced_prompt": "...",
  "model_used": "ollama/qwen2.5:7b",
  "detected_domain": "furniture",
  "generated_code": "import cadquery as cq\n...",
  "attempts": 2,
  "success": true,
  "time_taken_s": 42.1,
  "cost_usd": 0.0,
  "retry_history": [ ... ],
  "gen_usage": { "prompt_tokens": 1100, "completion_tokens": 1544 }
}
```

Logs include the final generated code even on failure, so you can inspect exactly what the model produced and why it was rejected.

---

## Domain Knowledge Base

`backend/cad_domains.json` contains **942 engineering domains** across 30+ categories (Aerospace, Automotive, Marine, Civil, Architecture, Industrial, Robotics, Electronics, Consumer, Medical, Oil & Gas, Mining, Agriculture, Defence, Rail, Furniture, Sports, Jewellery, Musical, Toys, Fashion, Packaging, Food, Plumbing, Scientific, Textile, Printing, Construction, Space Systems / Emerging).

When a prompt is submitted, a 3-phase scored search finds the top matching domains and injects a focused vocabulary fragment into the system prompt for that request. Re-generate the domain list:

```bash
# Set your OpenAI key, then:
python generate_domains.py
```

---

## Environment Variables

Create a `.env` file in `backend/` or set these in your shell:

```env
GEMINI_API_KEY=...
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GROQ_API_KEY=...
MISTRAL_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434   # optional, default shown
```

API keys can also be entered per-request in the Settings panel — they are used only for that request and stored in browser localStorage.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML / CSS / JS — no build step |
| 3D Preview | Three.js (STLLoader + OrbitControls) |
| Backend | FastAPI + Uvicorn |
| CAD Engine | CadQuery (OCCT kernel) |
| LLM Routing | LiteLLM |
| Local AI | Ollama |

---

## License

Copyright © 2026 Nilesh Sarkar.

