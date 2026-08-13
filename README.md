# Lexi Evaluator

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Last commit](https://img.shields.io/github/last-commit/DenisSeko/text-evaluator)](https://github.com/DenisSeko/text-evaluator)

A multi-agent AI application that evaluates **how well written** a piece of text from
the Lexi blog (https://lexi.hr/blog/) is. It takes a URL, extracts the clean article content, runs
**4 independent AI agents** — each with its own perspective and prompt — and combines their
scores into an overall score with per-agent rationale.

> Stack: Python 3.12 · CLI · OpenAI (with an abstraction layer for other providers)
> No database, no deployment, no authentication — focus on prompts and orchestration.

---

## How it works

```
URL ──► scraper ──► extractor ──► 4 agents (parallel) ──► synthesizer ──► report
              (httpx)   (trafilatura/     (OpenAI, JSON)     (final assessment)   (MD + JSON)
                        BeautifulSoup)
```

1. **Scraping** — `scraper.py` fetches the HTML (httpx, custom `User-Agent`, on-disk cache).
2. **Extraction** — `extractor.py` extracts the clean article content (title, author, date,
   headings, paragraphs) and discards navigation, footer, cookie banner and "Read more".
   `trafilatura` primary, `BeautifulSoup` fallback.
3. **Agents** — 4 independent agents, each with its own system prompt, rubric and JSON
   schema, run in parallel (`asyncio.gather`). See [docs/PROMPTS.md](docs/PROMPTS.md).
4. **Synthesizer** — 1 additional call that reads all verdicts and writes a final,
   balanced assessment with prioritized recommendations (optional, `--no-synth`).
5. **Scoring** — overall score = weighted average of agent scores, mapped to a
   letter grade A–F + label. See [Scoring system](#scoring-system).

### Agents

| Agent | Perspective | Criteria |
|---|---|---|
| **Structure and flow** | Does the text guide the reader logically through the content | Hook, Logical flow, Heading structure, Clarity, Pacing |
| **Writing psychology** | Psychological principles of good writing | Concreteness, Reader benefit, Tone, Anti-filler, Examples, Trust |
| **Quantitative rubric** | Fixed rubric, consistent scoring | Clarity, Structure, Specificity, Reader-benefit, Tone, Readability |
| **Human voice / anti-generic** | Does it sound human or AI-generic | Authenticity, Anti-cliché, Personal voice, AI-markers |

> Languages: **the whole report** — from the title and labels to criterion names, verdicts,
> strengths, weaknesses and notes — follows the auto-detected article language (HR or EN), with no
> English glosses. This applies to JSON (agent names, criteria) and Markdown
> (including the "chrome" — table headings, Strengths/Weaknesses, labels). Dates and times
> are localized too — HR form (e.g. "24. srpnja 2025.") or US
> ("July 24, 2025"); JSON stays ISO 8601.

### Scoring system

- Each agent returns a **0–10** score + criteria + strengths/weaknesses + rationale.
- **Overall score** = weighted average: structure **30%**, rubric **30%**,
  psychology **25%**, humanity **15%** (configurable via `.env`).
- If an agent fails, it is excluded and the weights are renormalized (doesn't crash the result).
- Letter grade + label:

| Score | Grade | Label |
|---|---|---|
| 9.0–10 | A | Excellent |
| 8.0–8.9 | B | Very good |
| 7.0–7.9 | C | Good |
| 6.0–6.9 | D | Adequate |
| 5.0–5.9 | E | Weak |
| 0–4.9 | F | Poor |

---

## Installation and usage (Windows / macOS / Linux)

### Prerequisite: Python 3.11+

- **Windows 10/11:** [python.org/downloads/windows](https://www.python.org/downloads/windows/)
  — during install tick **"Add Python to PATH"**.
- **macOS:** [python.org/downloads/macos](https://www.python.org/downloads/macos/)
- **Linux:** [python.org/downloads](https://www.python.org/downloads/) or a package manager
  (`sudo apt install python3 python3-venv python3-pip` on Debian/Ubuntu).

### Quick install

**Linux / macOS — directly through the terminal (curl, no manual cloning):**

```bash
curl -fsSL https://raw.githubusercontent.com/DenisSeko/text-evaluator/main/scripts/install.sh | bash
```

The script clones the repo (into `~/lexi`), creates `.venv`, installs dependencies +
CLI and creates `.env`. If the repo is hosted elsewhere, set the URL before running:

```bash
LEXI_REPO_URL="https://github.com/TVOJ-ORG/lexi" \
  curl -fsSL https://raw.githubusercontent.com/DenisSeko/text-evaluator/main/scripts/install.sh | bash
```

> Environment variables read by `install.sh` (all optional; the value in parentheses is the default):

| Variable | Default | Description |
|---|---|---|
| `LEXI_REPO_URL` | `https://github.com/DenisSeko/text-evaluator` | Repo cloned in direct-install mode |
| `LEXI_REPO_BRANCH` | `main` | Branch to clone |
| `LEXI_DIR` | `~/lexi` (Windows: `%USERPROFILE%\lexi`) | Target folder to clone into |

Example of cloning to another location:

```bash
LEXI_DIR="$HOME/Desktop/lexi-test" \
  curl -fsSL https://raw.githubusercontent.com/DenisSeko/text-evaluator/main/scripts/install.sh | bash
```

> **Security:** `curl | bash` executes a remote script. Inspect it first:
> `curl -fsSL <URL>` and review the output before piping it to `bash`.
> The script also works locally from the repo: `bash scripts/install.sh`.

**Windows 10/11** (from the project root folder):

```bat
:: cmd:          scripts\install.bat
:: PowerShell:   .\scripts\install.bat
```

> Note (PowerShell): scripts don't run from the current folder without the `.\` prefix.
> If you're already inside the `scripts\` folder, run `.\install.bat`.

> `install.bat` automatically adds a PowerShell **`lexi`** function to your profile
> (`$PROFILE`), so in a new terminal you can use `lexi "URL"` right away — without activation
> and without a full path.

**Activating the venv in PowerShell** (after `install.bat`, the venv is not active):

```powershell
# PowerShell may block .ps1 activation due to execution policy — allow it for the session:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
lexi --help
```

Or skip activation and use the full path:

```powershell
.\.venv\Scripts\lexi.exe --help
```

The scripts do everything automatically: create `.venv`, install pinned dependencies + the CLI command
`lexi`, and create `.env` from `.env.example` (just add the key).

### Manual installation

```bash
cd text-evaluator    # or the folder you cloned into
python3 -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt

# Install the CLI as a command (creates `lexi` on all three OSes)
python -m pip install -e .

# Configuration (the key is NEVER committed)
cp .env.example .env        # Windows: copy .env.example .env
# edit .env and set the real OPENAI_API_KEY
```

> After `pip install -e .` you have **the same command on Linux, macOS and Windows 10/11**:
> `lexi <URL>`. It works from any folder because `.env` is resolved relative to the
> project root (not the current directory). If you don't want to install, use
> `python -m lexi_evaluator <URL>` from the project root folder.

### Running

```bash
# Evaluate a real Lexi post (same command on all OSes)
lexi "https://lexi.hr/why-writing-sounds-generic/"

# Save the report as Markdown and/or JSON
lexi <URL> --output md  --out-file examples/run.md
lexi <URL> --output json --out-file examples/run.json

# Offline demo without an API key and without network (mock LLM + saved fixture)
lexi --dry-run --fixture tests/fixtures/sample_article.html
# or: python scripts/demo_dry.py

# Options
lexi <URL> --agents structure,rubric   # subset of agents
lexi <URL> --no-synth                  # without the final assessment
lexi <URL> --no-cache                  # without the HTML cache
lexi --help                            # all options
```

> **Testing note:** `--fixture` expects a path to an HTML file, and `--dry-run`
> is a separate flag — always use both: `--dry-run --fixture <path>`.

### Tests and lint

Run from the **project root folder** (`python -m` adds the root to `sys.path`,
so the package is importable):

```bash
python -m pytest -q          # offline: extractor, scoring, dry-run pipeline
python scripts/check_no_secrets.py   # honeypot: checks there are no keys in the repo
ruff check . && ruff format --check .
```

### (Optional) Standalone `.exe` (Windows 10/11)

If you want to distribute a **standalone `.exe` without a Python installation**, build it on
Windows (PyInstaller doesn't support cross-compilation, so it can't be built from Linux/macOS):

```powershell
.venv\Scripts\activate
python -m pip install pyinstaller
pyinstaller --onefile --name lexi lexi_evaluator\__main__.py
# result: dist\lexi.exe — run as:
#   dist\lexi.exe <URL>
# Note: for the key you still need .env in the working folder or an OPENAI_API_KEY env variable.
```

### CI/CD and pre-push checks

The repo has an **automated "code review" gate**:

- **GitHub Actions** (`.github/workflows/ci.yml`) — on every `push` to `main` and on every
  **pull request** it automatically checks on **Ubuntu** (free runner):
  `pytest` (offline, no key/network), `ruff check`, `ruff format --check` and honeypot scan.
  Without green checks a PR can't be "reviewed" as clean.

> **Status:** the workflow is set up and runs automatically on every `push`/PR.
> The same checks can also be run locally before pushing with `bash scripts/check_all.sh`.
- **Local gate before push** — run before `git push`:
  ```bash
  bash scripts/check_all.sh     # pytest + ruff + format + honeypot
  ```
- **Pre-push git hook** (optional, runs the gate automatically before every push):
  ```bash
  git config core.hooksPath .githooks
  ```

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI key (from an env variable, never in code/repo) |
| `LEXI_MODEL` | `gpt-4.1-mini` | Model for the 4 agents (cheap, good JSON) |
| `LEXI_MODEL_SYNTH` | `gpt-5-mini` | Model for the synthesizer (1 call per run) |
| `LEXI_MAX_CHARS` | `40000` | Truncate the article sent to the agents |
| `LEXI_TEMPERATURE` | `0.3` | Sampling temperature (lower = more consistent) |
| `LEXI_WEIGHT_*` | see above | Per-agent weights (sum = 1.0) |
| `LEXI_CACHE_DIR` | `.cache` | Raw HTML cache (gitignored) |
| `LEXI_REQUEST_TIMEOUT` | `60.0` | HTTP timeout for scraping (seconds) |

---

## Key security (IMPORTANT)

- The key is loaded exclusively from an **environment variable** or a gitignored `.env`.
- `.env` is in `.gitignore`; only `.env.example` with a placeholder goes in the repo.
- `scripts/check_no_secrets.py` scans the repo for `sk-proj-…` and similar patterns and
  fails if it finds anything — run it before every commit/push.
- **Never commit `.env` or the key.** If that happens, consider the key compromised.

---

## Project structure

> Detailed development guide (tree with explanations, "where is what", recipes for adding
> agents/providers, conventions): [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

```
lexi/
  lexi_evaluator/
    cli.py            # CLI entry (argparse) + run flow
    config.py         # pydantic-settings (.env, project-relative)
    models.py         # pydantic models (Article, AgentVerdict, EvaluationResult, ...)
    scraper.py        # httpx fetch + cache
    extractor.py      # trafilatura / BeautifulSoup cleans content + detect_language
    scoring.py        # aggregation + letter grade + renormalization
    orchestrator.py   # parallel agents + synthesizer
    report.py         # Markdown/JSON render (+ date localization)
    providers/        # LLM abstraction (OpenAI + Mock) + build_client
    agents/           # 4 agents (prompt + schema) + registry
  scripts/
    install.sh        # Linux/macOS installation (and curl | bash)
    install.bat       # Windows 10/11 installation
    check_no_secrets.py  # honeypot scan
    demo_dry.py       # offline demo → examples/
  tests/              # pytest (extractor, scoring, report, dry-run pipeline) + fixture
  examples/           # live reports from real Lexi posts (JSON + MD) + .gitkeep
  docs/
    PROMPTS.md        # all prompts verbatim + design rationale
    PLANNING.md       # original session plan
    DEVELOPMENT.md    # development guide (where/how/what)
  PLAN.md             # planning + architectural decisions (ADR)
  .github/workflows/ci.yml   # CI gate (pytest + ruff + honeypot)
  .githooks/                 # pre-push hook (optional)
```

## Decisions (briefly)

Details in [PLAN.md](PLAN.md). Key points:

- **CLI, not web** — the task asks for "no over-engineering" (no database/deploy/auth).
- **Python 3.12 + pip + pinned requirements** — cross-OS (Windows/macOS/Linux), no shell scripts.
- **`gpt-4.1-mini` for agents + `gpt-5-mini` for the synthesizer** — better cost/quality ratio
  than the older `gpt-4o-mini`; the absolute cost difference is negligible
  (a few cents per run). The model is easy to change via `.env`.
- **4 perspectives, not 3** — added "Human voice / anti-generic" because it's the core of the Lexi brand.
- **Synthesizer as the 5th call** — demonstrates agent collaboration; the deterministic sum
  gives the number, the synthesizer gives the narrative (optional).

---

## Example outputs

The `examples/` folder contains **live reports from real Lexi posts** (part of this repo),
while `demo-dry.*` (mock, no key/network) is generated locally and not committed:

- **Live run** (committed in the repo), for example:
  - `examples/lexi-why-writing-sounds-generic.{md,json}` → **7.0/10, C (Good)**
  - `examples/lexi-psiholoski-mehanizmi-iza-clickbaita.{md,json}` → **7.7/10, C (Good)**
  - `examples/lexi-how-to-respond-to-a-negative-review.{md,json}` → **7.7/10, C (Good)**
- **Offline demo** (mock, no key/network): `python scripts/demo_dry.py`
  → creates `examples/demo-dry.{md,json}` locally (gitignored)
- New live run for your own test: `lexi <URL> --output md --out-file examples/run.md`
  (and `--output json --out-file examples/run.json`)
