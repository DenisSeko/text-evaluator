#!/usr/bin/env bash
#
# Local pre-push gate — run this before pushing to GitHub.
# Mirrors what the CI workflow (.github/workflows/ci.yml) checks:
#   tests, ruff lint, ruff format, secret scan.
#
# Usage:  bash scripts/check_all.sh    (or:  ./scripts/check_all.sh)
# Optional: wire it into the pre-push git hook:
#   git config core.hooksPath .githooks
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY=.venv/bin/python
[ -x "$PY" ] || { echo "error: $PY not found — run scripts/install.sh first"; exit 1; }

echo "==> pytest"
"$PY" -m pytest -q

echo "==> ruff check"
.venv/bin/ruff check .

echo "==> ruff format --check"
.venv/bin/ruff format --check .

echo "==> secret honeypot scan"
"$PY" scripts/check_no_secrets.py

echo
echo "All checks passed — safe to push."
