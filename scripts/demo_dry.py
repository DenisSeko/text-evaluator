#!/usr/bin/env python3
"""Offline demo: run the full pipeline with the mock LLM on the bundled fixture.

No API key and no network needed. Writes both Markdown and JSON examples:

    python scripts/demo_dry.py                 (system python, uses venv if present)
    .venv/bin/python scripts/demo_dry.py       (Linux/macOS)
    .venv\\Scripts\\python.exe scripts\\demo_dry.py  (Windows)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "sample_article.html"
OUT_MD = ROOT / "examples" / "demo-dry.md"
OUT_JSON = ROOT / "examples" / "demo-dry.json"


def _python() -> str:
    """Prefer the project venv's python so all dependencies are available.

    On Windows the demo is often run with a system python that has no deps
    installed — falling back to the venv interpreter fixes that.
    """
    for candidate in (ROOT / ".venv" / "bin" / "python", ROOT / ".venv" / "Scripts" / "python.exe"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def run(*args: str) -> None:
    cmd = [_python(), "-m", "lexi_evaluator", *args]
    print(f"$ {' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        sys.exit(
            f"demo failed (exit {exc.returncode}).\n"
            "Is the venv set up? Run scripts/install.sh (or install.bat on Windows), then:\n"
            "  .venv\\Scripts\\python.exe scripts\\demo_dry.py"
        )


def _require(path: Path) -> None:
    """Fail loudly if an expected output file was not actually created."""
    if not path.exists() or path.stat().st_size == 0:
        sys.exit(f"error: expected output was not created: {path}")


def main() -> None:
    if not FIXTURE.exists():
        sys.exit(f"fixture not found: {FIXTURE} (run the extractor tests first?)")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    run("--fixture", str(FIXTURE), "--dry-run", "--output", "md", "--out-file", str(OUT_MD))
    _require(OUT_MD)
    run("--fixture", str(FIXTURE), "--dry-run", "--output", "json", "--out-file", str(OUT_JSON))
    _require(OUT_JSON)
    print(f"\nWrote:\n  {OUT_MD}\n  {OUT_JSON}")


if __name__ == "__main__":
    main()
