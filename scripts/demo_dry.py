#!/usr/bin/env python3
"""Offline demo: run the full pipeline with the mock LLM on the bundled fixture.

No API key and no network needed. Writes both Markdown and JSON examples:

    python scripts/demo_dry.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "sample_article.html"
OUT_MD = ROOT / "examples" / "demo-dry.md"
OUT_JSON = ROOT / "examples" / "demo-dry.json"


def run(*args: str) -> None:
    cmd = [sys.executable, "-m", "lexi_evaluator", *args]
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    if not FIXTURE.exists():
        sys.exit(f"fixture not found: {FIXTURE} (run the extractor tests first?)")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    run("--fixture", str(FIXTURE), "--dry-run", "--output", "md", "--out-file", str(OUT_MD))
    run("--fixture", str(FIXTURE), "--dry-run", "--output", "json", "--out-file", str(OUT_JSON))
    print(f"\nWrote:\n  {OUT_MD}\n  {OUT_JSON}")


if __name__ == "__main__":
    main()
