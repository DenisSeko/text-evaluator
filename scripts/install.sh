#!/usr/bin/env bash
#
# Lexi Evaluator — install script (Linux / macOS).
#
# Does everything automatically:
#   1. finds Python 3.11+
#   2. creates a .venv
#   3. installs pinned requirements (incl. dev/test tools) + the CLI command
#   4. creates .env from .env.example (you only add your OPENAI_API_KEY)
#
# Usage:  bash scripts/install.sh      (or:  ./scripts/install.sh)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Lexi Evaluator install (Linux/macOS)"

# --- 1. Python ---------------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "error: Python 3.11+ is required but was not found."
  echo "       macOS: https://www.python.org/downloads/macos/"
  echo "       Linux: https://www.python.org/downloads/"
  exit 1
fi

if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "error: need Python 3.11+ (found: $("$PY" --version 2>&1))."
  echo "       macOS: https://www.python.org/downloads/macos/"
  echo "       Linux: https://www.python.org/downloads/"
  exit 1
fi

# --- 2. venv -----------------------------------------------------------------
if [ ! -d .venv ]; then
  echo "==> Creating .venv"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# --- 3. Dependencies + CLI ---------------------------------------------------
echo "==> Installing pinned requirements (incl. dev/test tools)"
python -m pip install --quiet --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .

# --- 4. .env -----------------------------------------------------------------
if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example (edit it and add your OPENAI_API_KEY)"
  cp .env.example .env
fi

echo
echo "Done. Quick checks:"
echo "  lexi-evaluator --help"
echo "  lexi-evaluator --dry-run --fixture tests/fixtures/sample_article.html --output md"
echo "  python -m pytest -q"
echo "Next: edit .env and set OPENAI_API_KEY (it is never committed)."
