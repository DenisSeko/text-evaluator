#!/usr/bin/env python3
"""Honeypot guard: fail if any secret-like value is present in the repo.

Scans every non-ignored file for OpenAI/Anthropic key patterns and also checks
that no `.env` file is tracked by git. Run before committing / pushing:

    python scripts/check_no_secrets.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directories/files that are never scanned (gitignored or generated).
SKIP_DIRS = {
    ".git",
    ".venv",
    ".cache",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
}
SKIP_FILES = {".env", ".gitignore", ".env.example"}

# Patterns that look like API keys / secrets.
SECRET_PATTERNS = [
    re.compile(r"sk-proj-[A-Za-z0-9_\-]+"),  # OpenAI project keys
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI legacy keys
    re.compile(r"sk-ant-[A-Za-z0-9_\-]+"),  # Anthropic keys
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"(?i)api[_-]?key\s*=\s*['\"][A-Za-z0-9_\-]{16,}"),  # generic key= assignment
]


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.name in SKIP_FILES:
            continue
        files.append(path)
    return files


def scan_files() -> list[tuple[Path, str]]:
    hits: list[tuple[Path, str]] = []
    for path in iter_files():
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                hits.append((path, pattern.pattern))
    return hits


def tracked_env_files() -> list[str]:
    """Return any `.env`-style file tracked by git (should be none)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    tracked = [line for line in result.stdout.splitlines() if line.endswith(".env")]
    return tracked


def main() -> int:
    problems = 0

    hits = scan_files()
    if hits:
        print("ERROR: potential secrets found in the following files:")
        for path, pattern in hits:
            print(f"  - {path.relative_to(ROOT)}  (pattern: {pattern})")
        problems += 1
    else:
        print("OK: no secret-like patterns found in scanned files.")

    tracked = tracked_env_files()
    if tracked:
        print("ERROR: .env files are tracked by git — remove them from the index:")
        for name in tracked:
            print(f"  - {name}")
        problems += 1
    else:
        print("OK: no .env files tracked by git.")

    if problems:
        print(f"\nFAILED with {problems} problem(s). Do not commit until fixed.")
        return 1
    print("\nPASS: repo is clean of secrets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
