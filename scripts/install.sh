#!/usr/bin/env bash
#
# Lexi Evaluator — install script (Linux / macOS).
#
# Two ways to use it:
#   1. From inside a checkout:  bash scripts/install.sh   (or: ./scripts/install.sh)
#   2. Direct install via curl (no clone needed by hand):
#        curl -fsSL <RAW-URL-OF-THIS-FILE> | bash
#      The script then clones the repo itself (see LEXI_REPO_URL below).
#
# It finds Python 3.11+, creates a .venv, installs pinned requirements +
# the `lexi` CLI command, and creates .env from .env.example.
#
# Env overrides:
#   LEXI_REPO_URL  - git URL cloned by the direct curl install
#                    (default: https://github.com/DenisSeko/text-evaluator)
#   LEXI_REPO_BRANCH - branch to clone (default: main)
#   LEXI_DIR       - target directory for the direct curl install
#                    (default: $HOME/lexi)
set -euo pipefail

REPO_URL="${LEXI_REPO_URL:-https://github.com/DenisSeko/text-evaluator}"
REPO_BRANCH="${LEXI_REPO_BRANCH:-main}"
INSTALL_DIR="${LEXI_DIR:-$HOME/lexi}"

# --- 0. Running inside a checkout, or direct curl install? --------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"
if [ -f "$SCRIPT_DIR/../pyproject.toml" ]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  echo "==> Lexi Evaluator install in place: $ROOT"
else
  echo "==> Lexi Evaluator direct install"
  if [ ! -d "$INSTALL_DIR/.git" ]; then
    echo "==> Cloning $REPO_URL ($REPO_BRANCH) -> $INSTALL_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
  else
    echo "==> Repo already present in $INSTALL_DIR — updating"
    git -C "$INSTALL_DIR" pull --ff-only || echo "warn: could not pull (continuing)"
  fi
  ROOT="$INSTALL_DIR"
fi
cd "$ROOT"

echo "==> Lexi Evaluator install (Linux/macOS)"

# --- 1. Python ---------------------------------------------------------------
# On Git Bash (Windows) `python3` may be the Microsoft Store stub which is not
# real Python — so test each candidate actually runs, not just that it exists.
PY=""
# Try the Windows py launcher first (matches install.bat), then python3/python.
for cand in py python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import sys" >/dev/null 2>&1; then
    PY="$cand"
    break
  fi
done
if [ -z "$PY" ]; then
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
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
  # Git Bash / Windows: venv uses Scripts/ instead of bin/
  # shellcheck disable=SC1091
  source .venv/Scripts/activate
else
  echo "error: venv activation script not found (.venv/bin/activate or .venv/Scripts/activate)"
  exit 1
fi

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
echo "  lexi --help"
echo "  lexi --dry-run --fixture tests/fixtures/sample_article.html --output md"
echo "  python -m pytest -q"
echo "Next: edit .env and set OPENAI_API_KEY (it is never committed)."
