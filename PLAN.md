# PLAN.md — Planning, architecture and decisions

This document shows the **process** of building the task: how the project was planned, which
architectural decisions were made and why, and how AI was used during development.

---

## 1. What we build (spec)

The application evaluates how well a Lexi text is written using **multiple AI
agents**:

- **Input:** URL of a Lexi blog post or case study
- **Scraping:** fetch the page and extract the clean post content (without navigation, footer, etc.)
- **Multi-agent verification:** multiple agents, each with its own prompt and perspective,
  evaluate whether the text is well written
- **Output:** overall score + per-agent rationale

Given boundaries: no database, no deployment, no authentication; focus on prompts,
orchestration and solution cleanliness; a few LLM calls per run; the key must never
end up in the repo.

---

## 2. Key decisions (ADR — Architecture Decision Records)

### ADR-001: Python CLI, not a web app
**Decision:** a CLI tool run with `python -m lexi_evaluator <URL>`, output in Markdown + JSON.
**Why:** the spec explicitly asks for "no over-engineering" (no database, deploy, auth). CLI is the
smallest possible surface that makes the clean pipeline usable and testable.
A web UI (Streamlit/FastAPI) adds surface without extra value for the task grading.
**Rejected alternative:** FastAPI server — too much infrastructure, and the spec doesn't ask for a service.

### ADR-002: Standalone project, separate git repo
**Decision:** the project lives in its own root folder `lexi/` with its own git repo,
outside the monorepo where it originated.
**Why:** the task asks for a public GitHub repo; mixing with a service monorepo (CI, docs-sync,
pnpm workspace) brings risks and noise. Full isolation.
**Consequence:** its own `requirements.txt`, `.venv`, `.env`, `.gitignore`.

### ADR-003: Python 3.12, pip + pinned requirements, no shell scripts
**Decision:** `requirements.txt` with pinned versions; everything runs with `python -m ...`.
**Why:** cross-OS requirement (Windows/macOS/Linux). Plain Python with `pathlib` + UTF-8 works
everywhere; `uv`/`poetry` are options, but pip + pinned is the least dependencies and most predictable.
Ruff for lint/format (same standard as the environment the project came from).
**Addendum (from live verification):** `pyproject.toml` defines `[project.scripts]`
(`lexi = "lexi_evaluator.cli:main"`), so after `pip install -e .` there is the same
`lexi <URL>` command on all three OSes (creates `.venv/bin/lexi` on
Linux/macOS and `.venv\Scripts\lexi.exe` on Windows). `.env` is loaded relative
to the project root (`config.py`), not the CWD — the command works from any folder.
**Convenience:** there are optional install scripts `scripts/install.sh`
(Linux/macOS) and `scripts/install.bat` (Windows) — they automate venv + dependencies + `.env`.
They are pure convenience; the manual steps (in README) still work, so "no shell scripts"
as a principle for running the app remains. For distribution without a Python installation
the README documents building a standalone `.exe` (PyInstaller, must be done on
Windows — no cross-compilation).

### ADR-004: Scraping — trafilatura primary, BeautifulSoup fallback
**Decision:** `trafilatura.extract` as the primary extractor, fallback to targeted
BeautifulSoup extraction (`<article>`/`main`, H1–H3, `<p>`, blockquote, lists;
removing nav/footer/aside/cookie containers).
**Why:** the Lexi blog is WordPress; trafilatura is built exactly for such pages and
reliably removes boilerplate. The fallback ensures it works on unusual layouts too.
**Test:** fixture = real Lexi HTML; tests prove that "Kolačići", "Pročitaj još",
footer and "© 2026" do **not** leak into the article.

### ADR-005: 4 agents, not the minimal 3
**Decision:** structure, psychology, quantitative rubric + **human voice / anti-generic**.
**Why:** the third perspective is within the spec ("Scoring: quantitative scoring by criteria"),
but Lexi is a brand built on the message "why writing sounds generic" — so the generic/AI-writing
detector is the most relevant. Each agent has its own system prompt, rubric and
JSON schema; they run in parallel, so an extra agent costs almost nothing in time.
**Prompt rationale:** in detail in [docs/PROMPTS.md](docs/PROMPTS.md).

### ADR-006: Models — `gpt-4.1-mini` for agents, `gpt-5-mini` for the synthesizer
**Decision:** default agents = `gpt-4.1-mini`, synthesizer = `gpt-5-mini`, both via `.env`.
**Why:** the initial plan was `gpt-4o-mini` (cheap, reliable JSON), but that model
is outdated. Newer models follow the prompt notably better and return valid JSON, and **the absolute
cost difference is negligible** (articles are short, ~5 calls per run → a few cents).
The synthesizer has only 1 call per run, so it can cost a bit more for higher quality.
Everything is configurable — the code never hardcodes a model.
**Key note:** models are billed per token; changing the model requires no
extra setup on the company key.

### ADR-007: Deterministic aggregation + narrative synthesizer
**Decision:** overall score = weighted average of agent scores (structure 30%, rubric 30%,
psychology 25%, humanity 15%), mapped to A–F; the final narrative is written by the synthesizer.
**Why:** the number must be repeatable and transparent (every score can be explained by
weights and agent scores), and the synthesizer adds a human-readable judgement and prioritized
recommendations. This demonstrates "agent collaboration" — the 5th call, optional (`--no-synth`).
**Robustness:** if one agent fails, it is excluded and the weights are renormalized.

### ADR-008: Key security = honeypot guard
**Decision:** the key is read exclusively from env/`.env` (gitignored); `scripts/check_no_secrets.py`
scans all files for `sk-proj-…`, `sk-ant-…`, AWS and generic key patterns and checks
that no `.env` is in the git index; exit code ≠ 0 if it finds something.
**Why:** the repo is public; a committed key = disqualification. The guard mechanically prevents
it before every push.
**Also:** the code never logs the key; error messages don't contain the key value.

### ADR-009: LLM abstraction, but only OpenAI implemented
**Decision:** a thin `LLMClient` interface + `providers/`; OpenAI + Mock implemented.
**Why:** the spec allows other providers (Anthropic/Gemini/Ollama), but asks for focus.
The interface makes the pipeline provider-agnostic with no extra code; adding a provider = one class.
The Mock provider enables tests and demos **without a key and network**.

---

## 3. Scoring system

- Scale: **0–10** per agent; overall = weighted average.
- Letter grade: A ≥ 9.0, B ≥ 8.0, C ≥ 7.0, D ≥ 6.0, E ≥ 5.0, F < 5.0, with labels
  (Excellent … Poor).
- Each agent returns: `score`, `criteria[]` (name/score/note), `strengths[]`,
  `weaknesses[]`, `verdict` — so it's clear **why** the text got the score it got.
- **The review language** is auto-detected from the article (`extractor.detect_language`: Croatian
  diacritics `čćšžđ` → HR, otherwise EN) and passed to every agent's prompt — **the whole
  report** (verdict, strengths, weaknesses, notes and criterion names) is written **only in
  the article's language**, with no English glosses in parentheses. The **report "chrome"** (headings, labels,
  tables, agent names, A–F grade labels) follows the article language too: bilingual agent
  names (`name_hr/en`, `perspective_hr/en`) + the `_L`/`_GRADE_LABELS` dicts in `report.py`;
  for an HR article e.g. "Very good" → "Vrlo dobar".
- **Dates and times** in the report are localized per article language: HR long form
  ("24. srpnja 2025." / "u 22:09 (UTC)") for Croatian, US form ("July 24, 2025" /
  ", 22:09 (UTC)") for English (`report.format_date` / `format_datetime`; JSON stays
  ISO 8601 for machine readability).
- JSON is validated (pydantic) and retried as needed; on repeated failure the agent is
  marked as failed and doesn't crash the whole run.

## 4. Costs

- **~5 LLM calls per run:** 4 agents + 1 synthesizer (optional).
- Lexi posts are short (~450–1500 words); `LEXI_MAX_CHARS=40000` is the upper bound.
- With `gpt-4.1-mini` / `gpt-5-mini` the cost per evaluation is on the order of **a few cents**.
- Development saves calls: on-disk HTML cache, offline `--dry-run` with a mock LLM, network-free tests.

## 5. How AI was used in planning and development

The task explicitly encourages using AI. The process in this repo:

1. **Planning prompt** (before writing code) asked to: explore the workspace (where the project
   fits, what the conventions are), explore the Lexi blog structure, then make a plan with phases,
   decisions, files and verification. The result is this `PLAN.md` + `docs/PROMPTS.md`.
2. **Decisions are documented** as ADRs (above) — "why exactly this" is part of the deliverable.
3. **Agent prompts** are designed as a standalone artifact (see PROMPTS.md) — that's the
   core of the task and deliberately separated from code for easy reading and editing.
4. **Iterative verification:** pytest (offline), ruff, dry-run, honeypot — every step
   is verified before the next.

## 6. Verification

- [x] `pytest -q` — **23 tests**, offline (extractor on a real fixture, scoring,
  report localization, dry-run pipeline) — detailed list in [§6.1](#61-detailed-test-list)
  and in `tests/`. Run with `.venv/bin/python -m pytest -q` (or `python -m pytest -q`
  with an activated venv).
- [x] `ruff check .` + `ruff format --check .` — clean
- [x] `python scripts/demo_dry.py` — full pipeline without key/network, generates `examples/`
- [x] `python scripts/check_no_secrets.py` — no keys in the repo
- [x] Live run on a real Lexi post with a real key → `examples/` (key in `.env`)
  - 3 URLs (JSON + MD in `examples/`): `why-writing-sounds-generic`
    (**7.0/10, C — Good**), `psiholoski-mehanizmi-iza-clickbaita`
    (**7.7/10, C — Good**), `how-to-respond-to-a-negative-review`
    (**7.7/10, C — Good**)
- [x] CI/CD gate: `.github/workflows/ci.yml` (GitHub Actions, Ubuntu: pytest + ruff +
  format + honeypot) + local `scripts/check_all.sh` (validated) + pre-push hook
  (`git config core.hooksPath .githooks`)

### 6.1 Detailed test list

Run: `.venv/bin/python -m pytest -q` → **23 passed**. All tests are **offline**
(mock LLM, saved HTML fixture, no network and no API key).

**`tests/test_extractor.py` — extraction (10 tests)**
fixture = `tests/fixtures/sample_article.html` (real, trimmed Lexi HTML).

| Test | Checks |
|---|---|
| `test_article_extracted` | plain_text is non-empty, words > 50, char_count == len(plain_text) |
| `test_title_detected` | title exists and contains "generic" |
| `test_contains_article_body` | a real sentence from the article ("nobody wakes up"/"generic") survived |
| `test_boilerplate_removed` | "kolačići", "pročitaj još", "all rights reserved", "© 2026" do NOT leak |
| `test_headings_detected` | ≥1 heading, among them "generic" |
| `test_source_is_set` | source is "trafilatura" or "beautifulsoup" |
| `test_article_language` | detected "en" (the fixture is an English article) |
| `test_detect_language_english` | text without diacritics → "en" |
| `test_detect_language_croatian` | text with `čćšžđ` → "hr" |
| `test_detect_language_empty` | empty string → "en" |

**`tests/test_scoring.py` — score aggregation (4 tests)**

| Test | Checks |
|---|---|
| `test_weighted_mean` | weighted average 30/30/25/15 is correct and rounded to 2 decimals |
| `test_failed_agent_renormalises_weights` | failed agent (error!) is excluded, weights renormalize 50/50 |
| `test_all_failed_gives_zero` | all agents failed → 0.0 / F |
| `test_grade_bands` | mapping of all A–F thresholds → (grade, label) |

**`tests/test_report.py` — date and report chrome localization (7 tests)**

| Test | Checks |
|---|---|
| `test_format_date_croatian` | "2026-01-28" + hr → "28. siječnja 2026." |
| `test_format_date_american` | "2026-01-28" + en → "January 28, 2026" |
| `test_format_datetime_croatian` | ISO + hr → "10. kolovoza 2026. u 21:02 (UTC)" |
| `test_format_datetime_american` | ISO + en → "August 10, 2026, 21:02 (UTC)" |
| `test_format_date_unknown_value_passthrough` | "n/a"/"unknown" passes through unchanged |
| `test_report_chrome_localized_croatian` | HR article → HR chrome: headings, labels, tables, agents ("Vrlo dobar", "Kriterij/Ocjena/Obrazloženje", "Snage/Slabosti") |
| `test_report_chrome_localized_english` | EN article → EN chrome: "Overall score", "Criterion/Score/Rationale", "Strengths/Weaknesses"; no Croatian labels |

**`tests/test_pipeline_dry.py` — end-to-end pipeline with a mock LLM (2 tests)**

| Test | Checks |
|---|---|
| `test_dry_run_pipeline` | 4 verdicts without errors, scores 0–10, criteria and verdict exist, overall > 0 with a valid letter grade, synthesis exists, **4 agent calls + 1 synthesizer** |
| `test_dry_run_without_synthesizer` | only 2 selected agents, synthesis and synth model = None |

## 7. Model notes (from live verification)

- **`gpt-5` / o-series models don't accept a custom `temperature`** (only default 1).
  `OpenAIProvider` now recognizes reasoning models by prefix (`gpt-5`, `o1`, `o3`, `o4`, `o5`)
  and doesn't send `temperature`, with a safety net: if the API still rejects it, retry without the parameter.
  Other `BadRequestError`s are converted to `LLMError` so they don't crash the whole run
  (aligned with ADR-007 — a single agent's failure is isolated).

## 8. Known limitations / future work

- Providers: only OpenAI implemented; Anthropic/Gemini/Ollama require one class each.
- The extractor assumes textual content; video/infographics are not evaluated.
- Weights are fixed (configurable); A/B calibration of weights on a larger sample is future work.
- No rate-limit/retry policy toward `lexi.hr` (only `User-Agent` + cache) — enough for a demo.
