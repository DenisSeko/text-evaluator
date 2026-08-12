# PLANNING.md — Original session plan (planning in the repo)

> This document is the **original plan** made at the start of the task (planning with AI,
> before writing code) — moved from the working session into the repo as part of the deliverable
> ("include your planning in the repo"). The code already matches this plan; phases marked
> ✅ are done. Compact version with ADRs: [`PLAN.md`](../PLAN.md).

---

# Plan — Lexi AI Text Quality Evaluator (multi-agent)

## Context / TL;DR
A standalone Python CLI application that: (1) scrapes a Lexi blog post from a URL, (2) extracts the clean article content (without navigation/footer/cookie banner/"Read more"), (3) runs ≥4 AI agents with their own prompts/perspectives that score the text quality, (4) aggregates into an overall score + per-agent rationale. No DB/deploy/auth (per task). Python 3.12, pip + requirements.txt (pinned), Ruff. Cross-OS (Windows/macOS/Linux).

## Key decisions (confirmed with the user)
- **Location:** standalone project at `/home/work/Projects/lexi` — separate root and separate git repo (✅ done; moved out of the monorepo after initial setup).
- **Interface:** CLI (argparse), `python -m lexi_evaluator <URL>`, JSON + Markdown output to stdout/file. Cross-OS: plain Python, pathlib, UTF-8, no shell scripts.
- **Provider:** OpenAI default (given key) + a thin abstraction layer `providers/` ready for Anthropic/Gemini/Ollama (only OpenAI implemented; plus a Mock provider for offline runs).
- **Key security (CRITICAL / honeypot):** NEVER write the key into any repo file. `.env` gitignored, `.env.example` placeholder. `scripts/check_no_secrets.py` scans the repo for the `sk-proj-` pattern and fails. Verification `git status` + grep.
- **Cost:** ~5 LLM calls per run (4 agents + 1 synthesizer), agents on `gpt-4.1-mini`, synthesizer on `gpt-5-mini` (env `LEXI_MODEL` / `LEXI_MODEL_SYNTH`), article truncate at `LEXI_MAX_CHARS`, HTML cache in `.cache/` (gitignored). *(Note: the initial plan was `gpt-4o-mini`; after discussing newer models the default was raised to `gpt-4.1-mini` + `gpt-5-mini` — cost difference negligible, quality better.)*

## Architecture — phases (dependencies in parentheses)

### Phase 1 — Scaffold ✅
1. Create `lexi/` (requirements.txt pinned: httpx, beautifulsoup4, trafilatura, openai, pydantic, pydantic-settings, python-dotenv, pytest, ruff), `.env.example` (placeholder key), `.gitignore` (.env, .venv, __pycache__, .cache/), pyproject.toml (ruff config).
2. `git init` a new repo in the folder; Python venv `.venv`; pip install. ✅
3. `config.py` (pydantic-settings: OPENAI_API_KEY, LEXI_MODEL, LEXI_MODEL_SYNTH, LEXI_MAX_CHARS, agent weights). Clear error if the key is missing. ✅
4. `models.py` (pydantic): `Article`, `Criterion`, `AgentVerdict`, `EvaluationResult`. ✅

### Phase 2 — Scraper + extractor ✅
5. `scraper.py`: async httpx fetch, custom User-Agent, timeout, redirects, HTML cache by URL hash (`--no-cache` option). ✅
6. `extractor.py`: `trafilatura.extract` primary (WordPress-robust), BeautifulSoup fallback — `<article>` → main container; H1 title, H2/H3, `<p>`, blockquote, lists; remove nav/footer/aside/script/style/cookie containers. Output `Article` (title, author, published_at, read_time, plain_text, char_count, headings). ✅

### Phase 3 — LLM provider + agents/prompts ✅
7. `providers/base.py`: `LLMClient` (async `complete(messages, json_mode)`), `providers/openai_provider.py`: openai SDK, structured output/JSON (`response_format`), retry with backoff. `providers/mock_provider.py`: deterministic canned responses for `--dry-run`/tests. ✅
8. `agents/` — agent registry; each agent = id, name, perspective, system prompt, rubric, output schema. **4 agents:**
   - `structure.py` — Structure and flow: clarity, logical flow, intro→body→outro, headings, transitions, does it guide the reader. ✅
   - `psychology.py` — Writing psychology: concreteness/specificity, reader benefit, tone, emotion, avoiding generic, examples/stories, authority (Lexi brand). ✅
   - `rubric.py` — Quantitative rubric: fixed criteria (Clarity, Structure, Specificity, Reader-benefit, Tone/Voice, Readability), each 0-10 + a short rationale. ✅
   - `humanity.py` — Human voice / anti-generic: does it sound human/authentic vs AI-generic; cliché, robotic phrasing (the core of the Lexi message "why writing sounds generic"). ✅
9. `docs/PROMPTS.md` — all prompts verbatim + design rationale per agent (core of the task). ✅
10. Agent output JSON: `{score 0-10, criteria[{name,score,note}], strengths[], weaknesses[], verdict}` — validation (pydantic) + retry on parse failure. ✅

### Phase 4 — Orchestration, scoring, report, CLI ✅
11. `orchestrator.py`: asyncio runs agents in parallel (gather) → optional synthesizer agent (reads all verdicts → final assessment + top recommendations; `--no-synth` flag). ✅
12. `scoring.py`: combined score = weighted average of agent scores (structure .3, rubric .3, psychology .25, humanity .15, configurable) → 0-10 mapped to letter grade A–F + label (Excellent…Poor) with documented thresholds. Transparent: why the score. ✅
13. `report.py`: JSON (structured, full) + Markdown (human-readable, per-agent rationale + overall). ✅
14. `cli.py` + `__main__.py`: `python -m lexi_evaluator <url> [--output json|md] [--out-file PATH] [--model NAME] [--synth-model NAME] [--agents ...] [--no-synth] [--no-cache] [--dry-run] [--fixture PATH] [--max-chars N]`. `--dry-run` = canned/mocked agent output without a key (for demo/CI/test). ✅

### Phase 5 — Documentation ✅
15. `README.md`: run instructions per OS (Windows/macOS/Linux), architecture, decisions, security, example output. ✅
16. `PLAN.md`: plan + ADRs + how AI was used (planning prompts) + cost analysis. ✅
17. `docs/PROMPTS.md` (see step 9). ✅

### Phase 6 — Tests, example, security verification (partly ✅, live run ⏳)
18. `tests/fixtures/sample_article.html` — saved (trimmed) real Lexi HTML; `tests/test_extractor.py` (assert contains the article, does NOT contain "Kolačići"/"Pročitaj još"/footer), `tests/test_scoring.py` (aggregation math), `tests/test_pipeline_dry.py` (dry-run with mock LLM, no network). ✅ (12 tests, green)
19. `scripts/check_no_secrets.py` — honeypot scan. ✅ (PASS)
20. ✅ Live run: `python -m lexi_evaluator https://lexi.hr/why-writing-sounds-generic/` → commit `examples/lexi-why-writing-sounds-generic.json` + `.md` (key in `.env`). Live evaluations were done on all 3 URLs from the plan (below) — results committed in `examples/` (later removed from the repo — the folder is kept empty, only `.gitkeep`).
21. Ruff check/format; pytest green; honeypot clean; `git status` without `.env`. ✅ (including live runs)

## Relevant files (full paths — new)
- `lexi_evaluator/scraper.py`, `extractor.py` — scraping and content cleaning
- `lexi_evaluator/providers/{base,openai_provider,mock_provider}.py` — LLM layer
- `lexi_evaluator/agents/{structure,psychology,rubric,humanity}.py` — agents + prompts
- `lexi_evaluator/orchestrator.py`, `scoring.py`, `report.py`, `cli.py` — orchestration/output
- `docs/PROMPTS.md`, `PLAN.md`, `PLANNING.md`, `README.md` — "planning" deliverable per task
- `scripts/check_no_secrets.py` — honeypot guard

## Verification
1. ✅ `cd lexi && .venv/bin/pytest -q` — offline, green (12 passed).
2. ✅ `.venv/bin/ruff check . && .venv/bin/ruff format --check .` — clean.
3. ✅ `.venv/bin/python -m lexi_evaluator https://lexi.hr/why-writing-sounds-generic/ --out-file examples/...` (live, with key) → valid JSON + MD (overall 7.0/10, C — Good).
4. ✅ `.venv/bin/python -m lexi_evaluator <url> --dry-run` (or `--fixture`) — pipeline without key/network.
5. ✅ `python scripts/check_no_secrets.py` → 0 found; `git status --porcelain` without `.env`.
6. ✅ Test on the 3 listed URLs (why-writing-sounds-generic, psiholoski-mehanizmi-iza-clickbaita, how-to-respond-to-a-negative-review) — live, with key in `.env`. Results: 7.0 / 7.7 / 7.7 (JSON + MD in `examples/`, later removed from the repo).

## Scope
- IN: scraper+extractor, 4 agents, scoring, CLI, docs, tests, example output, honeypot guard.
- IN (added later, after the task was done): CI/CD gate — GitHub Actions
  (`.github/workflows/ci.yml`, Ubuntu) + local gate `scripts/check_all.sh` + pre-push hook.
- OUT (per task, "don't over-engineer"): database, deploy, auth, web UI, additional providers
  (only a documented seam).

## Further considerations
1. ✅ Model: `gpt-4.1-mini` for agents + `gpt-5-mini` for the synthesizer (configurable via `.env`); the initial `gpt-4o-mini` recommendation was replaced after discussing newer models.
2. ✅ Output language: the whole report (verdict, strengths, weaknesses, notes and criterion names) **only in the article's language**, with no English glosses in parentheses. Dates/times are localized per article language (HR long form / US form; JSON stays ISO). The language is **auto-detected** from the article (heuristic: Croatian diacritics `čćšžđ` → HR, otherwise EN; `extractor.detect_language`) and passed to every agent's prompt (`agents/base.build_messages`), so the model writes the whole review in the article's language.
3. ✅ Git: standalone repo in `lexi/` (branch `main`), moved out of the monorepo.
