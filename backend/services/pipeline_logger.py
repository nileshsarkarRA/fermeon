"""
Fermeon — Pipeline Logger
Consistent terminal status output for the 5-stage CAD generation pipeline.

Format:
  ▶ [model] stage name...
    ✓ tokens  elapsed
    ✗ failure reason

  ━━━━━━━━━━━━━━━━━━━━━━━━
    PIPELINE ATTEMPT 1/3
  ━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

SEP = "━" * 56
LINE = "─" * 56


def stage(name: str, model: str | None = None, extra: str = "") -> None:
    """Print stage start: ▶ [model] name..."""
    if model:
        print(f"▶ [{model}] {name}...{extra}", flush=True)
    else:
        print(f"▶ {name}...{extra}", flush=True)


def ok(*parts) -> None:
    """Print stage success: ✓ part1  part2  ..."""
    msg = "  ".join(str(p) for p in parts if p is not None and str(p) != "")
    print(f"  ✓ {msg}", flush=True)


def fail(reason: str) -> None:
    """Print stage failure: ✗ reason"""
    # Truncate very long errors for readability
    display = reason[:120] + "..." if len(reason) > 120 else reason
    print(f"  ✗ {display}", flush=True)


def attempt_header(n: int, total: int) -> None:
    """Print attempt separator banner."""
    print(f"\n{SEP}", flush=True)
    print(f"  PIPELINE ATTEMPT {n}/{total}", flush=True)
    print(f"{SEP}\n", flush=True)


def job_start(job_id: str, prompt: str) -> None:
    """Print job start header."""
    preview = (prompt[:58] + "...") if len(prompt) > 58 else prompt
    print(f"\n{LINE}", flush=True)
    print(f"  JOB {job_id}", flush=True)
    print(f'  "{preview}"', flush=True)
    print(f"{LINE}", flush=True)


def cem_banner(cem_name: str) -> None:
    """Print CEM fast-path banner."""
    print(f"\n{LINE}", flush=True)
    print(f"  CEM ▶  {cem_name}  (zero-failure path)", flush=True)
    print(f"{LINE}", flush=True)


def final_success(job_id: str, paths: dict, attempts: int, elapsed: float) -> None:
    """Print final success summary."""
    fmts = " + ".join(k.upper() for k, v in paths.items() if v)
    attempt_word = "attempt" if attempts == 1 else "attempts"
    print(f"\n{SEP}", flush=True)
    print(f"  ✅  {fmts} exported — {attempts} {attempt_word}  {elapsed:.1f}s", flush=True)
    for _fmt, path in paths.items():
        if path:
            print(f"  → {path}", flush=True)
    print(f"{SEP}\n", flush=True)


def final_failure(attempts: int, reason: str) -> None:
    """Print final failure summary."""
    attempt_word = "attempt" if attempts == 1 else "attempts"
    print(f"\n{SEP}", flush=True)
    print(f"  ❌  FAILED after {attempts} {attempt_word}", flush=True)
    if reason:
        display = reason[:150] + "..." if len(reason) > 150 else reason
        print(f"     {display}", flush=True)
    print(f"{SEP}\n", flush=True)
