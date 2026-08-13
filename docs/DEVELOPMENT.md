# DEVELOPMENT.md — Development guide

> How to navigate the code: **where is what**, **how to add what** and **which conventions** to follow.
> Read this first: [`README.md`](../README.md) (how to run) and [`PLAN.md`](../PLAN.md)
> (why exactly this — the ADRs). Agent prompts (the core of the task) are in [`PROMPTS.md`](./PROMPTS.md).

---

## 1. Mental model

One CLI call = one evaluation run:

```
URL → scraper → extractor → Article
                              │  (article language: hr / en)
                              ▼
       4 agents (parallel) ──► 4 × AgentVerdict ──► scoring (weighted) ──► OverallScore
                              │                          │
                              └─────────► synthesizer ──►┘
                                                   ▼
                                        EvaluationResult ──► report ──► Markdown + JSON
```

- All main entities the pipeline carries are defined in **`models.py`**.
- All input parameters (models, weights, key) come from **`.env`** via **`config.py`** — the code never hardcodes them.
- The pipeline is async (`asyncio`); agents run in parallel, `--dry-run` uses a mock provider (no key/network).

---

## 2. Project tree (with explanations)

```
lexi-evaluator/
├── README.md                 # user instructions: install, run, tests
├── PLAN.md                   # planning + ADRs ("why exactly this")
├── pyproject.toml            # package, [project.scripts] (command), ruff + pytest config
├── requirements.txt          # runtime dependencies (pinned)
├── requirements-dev.txt      # test/lint: pytest, pytest-asyncio, ruff
├── .env.example              # TEMPLATE for .env — never a real key!
├── .gitignore
├── .github/
│   └── workflows/ci.yml      # CI gate (pytest + ruff + honeypot) on push/PR
├── .githooks/                # pre-push hook (optional)
├── lexi_evaluator/           # ← main package
│   ├── __main__.py           # python -m lexi_evaluator → cli.main()
│   ├── cli.py                # argparse + run flow (fetch → extract → evaluate → render)
│   ├── config.py             # pydantic-settings; .env (project-relative); weights, models, key
│   ├── models.py             # pydantic types: Article, Criterion, AgentVerdict, OverallScore, EvaluationResult
│   ├── scraper.py            # httpx fetch (User-Agent, timeout) + HTML cache
│   ├── extractor.py          # trafilatura / BS4 → clean Article; detect_language()
│   ├── orchestrator.py       # parallel agents (gather) + synthesizer → EvaluationResult
│   ├── scoring.py            # weighted average, A–F grade, renormalization of failures
│   ├── report.py             # Markdown render (+ date localization) and to_json()
│   ├── agents/               # ← evaluation agents (perspectives)
│   │   ├── __init__.py       # REGISTRY: AGENTS dict + get_agents()
│   │   ├── base.py           # Agent ABC; build_messages (language instruction); parse_verdict (pydantic)
│   │   ├── structure.py      # Structure and flow
│   │   ├── psychology.py     # Writing psychology
│   │   ├── rubric.py         # Quantitative rubric
│   │   └── humanity.py       # Human voice / anti-generic
│   └── providers/            # ← LLM abstraction
│       ├── __init__.py       # build_client(settings, dry_run, model)
│       ├── base.py           # LLMClient ABC; LLMError, LLMParseError
│       ├── openai_provider.py# OpenAI (JSON mode, retry, temperature for gpt-5/o-series)
│       └── mock_provider.py  # deterministic canned responses (--dry-run / tests)
├── scripts/
│   ├── install.sh            # Linux/macOS installation (and curl | bash)
│   ├── install.bat           # Windows 10/11 installation
│   ├── check_no_secrets.py   # honeypot: scans the repo for keys
│   └── demo_dry.py           # offline demo (mock) → regenerates examples/
├── tests/
│   ├── conftest.py           # fixture sample_article.html (real Lexi HTML)
│   ├── test_extractor.py     # extraction (without boilerplate) + detect_language
│   ├── test_scoring.py       # aggregation / grade math
│   ├── test_report.py        # date localization (HR/US)
│   └── test_pipeline_dry.py  # full pipeline with a mock LLM, no network
├── examples/                 # live reports from real Lexi posts (JSON + MD); demo-dry.* local
└── docs/
    ├── PROMPTS.md            # all prompts verbatim + design rationale
    ├── PLANNING.md           # original session plan
    └── DEVELOPMENT.md        # ← THIS — development guide
```

---

## 3. "Where is what" (quick map)

| You want to change... | File(s) |
|---|---|
| **An agent's prompt** | `lexi_evaluator/agents/<id>.py` (and `docs/PROMPTS.md`) |
| **Add a new agent** | new `agents/<id>.py` + registry `agents/__init__.py` + weight in `.env` |
| **Weights / aggregation** | `.env` (`LEXI_WEIGHT_*`) + `config.py`; logic in `scoring.py` |
| **Grade thresholds (A–F)** | `scoring.py` → `GRADE_BANDS` |
| **Add an LLM provider** | new `providers/<x>.py` + `build_client` in `providers/__init__.py` |
| **Model for agents/synthesizer** | `.env` (`LEXI_MODEL`, `LEXI_MODEL_SYNTH`) |
| **New CLI option** | `cli.py` (argparse + `_run`) |
| **Report look/format** | `report.py` (MD), `models.py` (JSON structure) |
| **Language/localization** | `extractor.detect_language`, `agents/base.build_messages`, `report.format_date/format_datetime` |
| **Scraping / extraction** | `scraper.py`, `extractor.py` |
| **Key security / a new secret** | `config.py`, `.env.example`, `scripts/check_no_secrets.py` |
| **New env variable** | `config.py` (field + alias) + `.env.example` |

---

## 4. Key types (`models.py`)

| Type | What it's for |
|---|---|
| `Article` | cleaned article: url, title, author, published_at, plain_text, word_count, headings, **language** |
| `Criterion` | one criterion: name, score 0–10, note |
| `AgentVerdict` | agent output: score, criteria[], strengths[], weaknesses[], verdict, error |
| `OverallScore` | aggregate: score, letter_grade, label, weights, agent_scores |
| `EvaluationResult` | the whole run result: article, model, agent_verdicts, overall, synthesis, created_at |

The JSON report = `EvaluationResult.model_dump(mode="json")` (keys = field names).

---

## 5. Recipes — how to add something new

### 5.1 New agent

1. **Create `lexi_evaluator/agents/novi.py`:**
   ```python
   from .base import Agent

   _JSON_SCHEMA = """{ "score": number, "criteria": [{"name": string, "score": number, "note": string}],
     "strengths": [string], "weaknesses": [string], "verdict": string }"""

   class NoviAgent(Agent):
       id = "novi"
       name = "Nova perspektiva"
       perspective = "One sentence about the perspective."

       def system_prompt(self) -> str:
           return "You are LexiEval... (in English, canonical)"

       def build_user_prompt(self, article_text: str) -> str:
           return f"""<ARTICLE>\n{article_text}\n</ARTICLE>\n... {_JSON_SCHEMA}"""

   novi_agent = NoviAgent()
   ```
   > Keep criterion names in the prompt **canonical in English** — the article language is localized
   > automatically in `Agent.build_messages` (see §6). Don't hardcode a Croatian criterion name.

2. **Register it in `agents/__init__.py`:**
   ```python
   from .novi import novi_agent
   AGENTS = {a.id: a for a in (structure_agent, psychology_agent, rubric_agent, humanity_agent, novi_agent)}
   ```

3. **Add a weight** in `.env` (`LEXI_WEIGHT_NOVI=0.20`) and a field + `agent_weights()` in `config.py`
   (adjust the other weights so the sum = 1.0; the renormalization logic is in `scoring.py`).

4. **Test** offline: `lexi --dry-run --fixture tests/fixtures/sample_article.html --agents novi`
   (mock returns deterministic JSON).

### 5.2 New LLM provider

1. **Create `providers/novi_provider.py`** — implement `LLMClient.complete`:
   ```python
   from .base import LLMClient

   class NoviProvider(LLMClient):
       name = "novi"
       def __init__(self, api_key, model, *, temperature=0.3, timeout=60.0): ...
       async def complete(self, messages, *, json_mode=False, temperature=None) -> str:
           # json_mode=True → request strict JSON (response_format/equivalent)
           ...
   ```
   See `openai_provider.py` as a reference (retry, JSON mode, temperature for reasoning models).

2. **Wire it into `build_client`** (`providers/__init__.py`) + add env variables/model in `config.py`
   and `.env.example`.

### 5.3 Changing weights or grade thresholds

- **Weights:** `.env` → `LEXI_WEIGHT_*` (defaults in `config.py`, must sum to 1.0).
- **A–F thresholds / labels:** `scoring.py` → `GRADE_BANDS`.

### 5.4 New CLI option

In `cli.py`: add `parser.add_argument(...)` in `build_parser`, read the value in `_run`,
then pass it to `evaluate(...)` (orchestration) or to the render part. Document the new option in README.

### 5.5 New test

Add it under `tests/` (e.g. `test_<module>.py`). Use `python -m pytest -q`.
Dry-run/tests **must not** depend on network or a key — use `MockProvider`/`--dry-run`.

### 5.6 Localization / language

- Language detection: `extractor.detect_language` (heuristic `čćšžđ` → hr, otherwise en).
- Language instruction for the LLM: `agents/base.build_messages` (one central place).
- **The whole report follows the article language** (HR or EN):
  - LLM content (verdict, strengths, weaknesses, notes and criterion names) — the prompt
    localizes it in `build_messages`.
  - Report "chrome" (headings, labels, tables, "Strengths/Weaknesses", ...) —
    the `_L` dict in `report.py` (`render_markdown`), selected by `article.language`.
  - Agent names/perspectives — bilingual attributes `name_hr/en`, `perspective_hr/en`
    on every agent; `orchestrator` writes the localized version into `AgentVerdict`
    (so JSON is consistent in the article language too).
  - Grade label (Excellent…Poor) — `_GRADE_LABELS` in `report.py` (e.g. "Vrlo dobar").
- Dates/times: `report.format_date` / `format_datetime` (HR long form / US);
  JSON stays ISO 8601.

### 5.7 Security (a new secret / env var)

- Add a field in `config.py` + a placeholder in `.env.example` (`.env` is gitignored).
- **Before every commit/push** run: `python scripts/check_no_secrets.py`.
- Error messages must never contain the key value.

---

## 6. Conventions

- Python **3.11+**, `from __future__ import annotations`, `pathlib`, UTF-8 — cross-OS (Win/mac/Linux).
- Lint/format: **Ruff** (`ruff check . && ruff format --check .`), line length 100, E501 ignored.
- **LLM JSON is validated with pydantic** (`AgentOutput`), on failure → `LLMParseError`;
  retry in the provider; **one agent's failure doesn't crash the whole run** (ADR-007).
- **Never hardcode a model or a key** — everything via `.env`/`config.py` (ADR-006, ADR-008).
- **Prompts:** canonical EN criterion names in prompts; the whole report is localized to
  the article language at runtime (ADR-005 addendum).
- Tests are offline, deterministic (mock), no network/key.

---

## 7. Commands (quick reference)

```bash
# running
lexi <URL>                                            # live run (MD to stdout)
lexi <URL> --output json --out-file rezultat.json     # JSON to a file
lexi --dry-run --fixture tests/fixtures/sample_article.html   # offline (mock)
lexi --help

# quality
python -m pytest -q                     # tests (23)
ruff check . && ruff format --check .   # lint + format
python scripts/check_no_secrets.py      # honeypot (required before push)
python scripts/demo_dry.py              # regenerates examples/demo-dry.*

# CI / pre-push gate
bash scripts/check_all.sh               # pytest + ruff + format + honeypot (local gate)
git config core.hooksPath .githooks     # once: pre-push hook runs check_all.sh
```

**CI/CD:** `.github/workflows/ci.yml` (GitHub Actions) runs the same checks on every
push/PR on **Ubuntu** — that's the automated "code review" (without green checks
a PR isn't considered clean). The local gate `scripts/check_all.sh` mirrors it before push.
