# DEVELOPMENT.md — Vodič za razvoj

> Kako se snaći u kodu: **gdje je što**, **kako što dodati** i **koje konvencije** slijediti.
> Prije ovog pročitaj: [`README.md`](../README.md) (kako pokrenuti) i [`PLAN.md`](../PLAN.md)
> (zašto baš tako — ADR-ovi). Prompte agenata (srž zadatka) vidi u [`PROMPTS.md`](./PROMPTS.md).

---

## 1. Mentalni model

Jedan CLI poziv = jedan evaluacijski run:

```
URL → scraper → extractor → Article
                              │  (jezik članka: hr / en)
                              ▼
       4 agenta (paralelno) ──► 4 × AgentVerdict ──► scoring (težinski) ──► OverallScore
                              │                          │
                              └─────────► sintetizator ──►┘
                                                   ▼
                                        EvaluationResult ──► report ──► Markdown + JSON
```

- Sve glavne entitete koje pipeline prenosi definira **`models.py`**.
- Svi ulazni parametri (modeli, težine, ključ) dolaze iz **`.env`** preko **`config.py`** — kod ih nikad ne hardkodira.
- Pipeline je async (`asyncio`); agenti se pokreću paralelno, `--dry-run` koristi mock provider (bez ključa/mreže).

---

## 2. Stablo projekta (s objašnjenjima)

```
lexi/
├── README.md                 # upute za korisnika: instalacija, pokretanje, testovi
├── PLAN.md                   # planiranje + ADR-ovi ("zašto tako")
├── pyproject.toml            # paket, [project.scripts] (komanda), ruff + pytest konfig
├── requirements.txt          # runtime ovisnosti (pinned)
├── requirements-dev.txt      # test/lint: pytest, pytest-asyncio, ruff
├── .env.example              # TEMPLATE za .env — nikad pravi ključ!
├── .gitignore
├── .github/
│   └── workflows/ci.yml      # CI gate (pytest + ruff + honeypot) na push/PR
├── .githooks/                # pre-push hook (opcionalno)
├── lexi_evaluator/           # ← glavni paket
│   ├── __main__.py           # python -m lexi_evaluator → cli.main()
│   ├── cli.py                # argparse + tok run-a (fetch → extract → evaluate → render)
│   ├── config.py             # pydantic-settings; .env (projekt-relative); težine, modeli, ključ
│   ├── models.py             # pydantic tipovi: Article, Criterion, AgentVerdict, OverallScore, EvaluationResult
│   ├── scraper.py            # httpx fetch (User-Agent, timeout) + HTML cache
│   ├── extractor.py          # trafilatura / BS4 → čisti Article; detect_language()
│   ├── orchestrator.py       # paralelni agenti (gather) + sintetizator → EvaluationResult
│   ├── scoring.py            # težinski prosjek, grade A–F, renormalizacija neuspjelih
│   ├── report.py             # render Markdown (+ lokalizacija datuma) i to_json()
│   ├── agents/               # ← evaluacijski agenti (perspektive)
│   │   ├── __init__.py       # REGISTAR: AGENTS dict + get_agents()
│   │   ├── base.py           # Agent ABC; build_messages (jezična instrukcija); parse_verdict (pydantic)
│   │   ├── structure.py      # Struktura i tok
│   │   ├── psychology.py     # Psihologija pisanja
│   │   ├── rubric.py         # Kvantitativna rubrika
│   │   └── humanity.py       # Ljudski glas / anti-generic
│   └── providers/            # ← LLM apstrakcija
│       ├── __init__.py       # build_client(settings, dry_run, model)
│       ├── base.py           # LLMClient ABC; LLMError, LLMParseError
│       ├── openai_provider.py# OpenAI (JSON mode, retry, temperature za gpt-5/o-seriju)
│       └── mock_provider.py  # deterministički canned odgovori (--dry-run / testovi)
├── scripts/
│   ├── install.sh            # instalacija Linux/macOS (i curl | bash)
│   ├── install.bat           # instalacija Windows 10/11
│   ├── check_no_secrets.py   # honeypot: scan repoa na ključeve
│   └── demo_dry.py           # offline demo (mock) → regenerira examples/
├── tests/
│   ├── conftest.py           # fixture sample_article.html (pravi Lexi HTML)
│   ├── test_extractor.py     # ekstrakcija (bez boilerplate-a) + detect_language
│   ├── test_scoring.py       # matematika agregacije / grade
│   ├── test_report.py        # lokalizacija datuma (HR/US)
│   └── test_pipeline_dry.py  # cijeli pipeline s mock LLM-om, bez mreže
├── examples/                 # živi izvještaji s realnih Lexi postova (JSON + MD); demo-dry.* lokalno
└── docs/
    ├── PROMPTS.md            # svi promptovi verbatim + razlog dizajna
    ├── PLANNING.md           # originalni plan sesije
    └── DEVELOPMENT.md        # ← OVO — vodič za razvoj
```

---

## 3. "Gdje je što" (brza mapa)

| Želiš promijeniti... | Fajl(ovi) |
|---|---|
| **Prompt nekog agenta** | `lexi_evaluator/agents/<id>.py` (i `docs/PROMPTS.md`) |
| **Dodati novog agenta** | novi `agents/<id>.py` + registar `agents/__init__.py` + težina u `.env` |
| **Težine / agregaciju** | `.env` (`LEXI_WEIGHT_*`) + `config.py`; logika u `scoring.py` |
| **Pragove ocjena (A–F)** | `scoring.py` → `GRADE_BANDS` |
| **Dodati LLM provider** | novi `providers/<x>.py` + `build_client` u `providers/__init__.py` |
| **Model za agente/sintetizator** | `.env` (`LEXI_MODEL`, `LEXI_MODEL_SYNTH`) |
| **Novu CLI opciju** | `cli.py` (argparse + `_run`) |
| **Izgled/format izvještaja** | `report.py` (MD), `models.py` (JSON struktura) |
| **Jezik/lokalizaciju** | `extractor.detect_language`, `agents/base.build_messages`, `report.format_date/format_datetime` |
| **Scraping / ekstrakciju** | `scraper.py`, `extractor.py` |
| **Sigurnost ključa / novu tajnu** | `config.py`, `.env.example`, `scripts/check_no_secrets.py` |
| **Novu env varijablu** | `config.py` (polje + alias) + `.env.example` |

---

## 4. Ključni tipovi (`models.py`)

| Tip | Čemu služi |
|---|---|
| `Article` | očišćeni članak: url, title, author, published_at, plain_text, word_count, headings, **language** |
| `Criterion` | jedan kriterij: name, score 0–10, note |
| `AgentVerdict` | output agenta: score, criteria[], strengths[], weaknesses[], verdict, error |
| `OverallScore` | agregat: score, letter_grade, label, weights, agent_scores |
| `EvaluationResult` | cijeli rezultat run-a: article, model, agent_verdicts, overall, synthesis, created_at |

JSON izvještaj = `EvaluationResult.model_dump(mode="json")` (ključevi = nazivi polja).

---

## 5. Recepti — kako dodati nešto novo

### 5.1 Novi agent

1. **Kreiraj `lexi_evaluator/agents/novi.py`:**
   ```python
   from .base import Agent

   _JSON_SCHEMA = """{ "score": number, "criteria": [{"name": string, "score": number, "note": string}],
     "strengths": [string], "weaknesses": [string], "verdict": string }"""

   class NoviAgent(Agent):
       id = "novi"
       name = "Nova perspektiva"
       perspective = "Jedna rečenica o perspektivi."

       def system_prompt(self) -> str:
           return "You are LexiEval... (na engleskom, kanonski)"

       def build_user_prompt(self, article_text: str) -> str:
           return f"""<ARTICLE>\n{article_text}\n</ARTICLE>\n... {_JSON_SCHEMA}"""

   novi_agent = NoviAgent()
   ```
   > Nazivi kriterija u promptu drži **kanonski na engleskom** — jezik članka se lokalizira
   > automatski u `Agent.build_messages` (vidi §6). Nemoj hardkodirati hrvatski naziv kriterija.

2. **Registriraj u `agents/__init__.py`:**
   ```python
   from .novi import novi_agent
   AGENTS = {a.id: a for a in (structure_agent, psychology_agent, rubric_agent, humanity_agent, novi_agent)}
   ```

3. **Dodaj težinu** u `.env` (`LEXI_WEIGHT_NOVI=0.20`) i polje + `agent_weights()` u `config.py`
   (ostale težine prilagodi da zbroj = 1.0; logika renormalizacije je u `scoring.py`).

4. **Testiraj** offline: `lexi --dry-run --fixture tests/fixtures/sample_article.html --agents novi`
   (mock vraća deterministički JSON).

### 5.2 Novi LLM provider

1. **Kreiraj `providers/novi_provider.py`** — implementiraj `LLMClient.complete`:
   ```python
   from .base import LLMClient

   class NoviProvider(LLMClient):
       name = "novi"
       def __init__(self, api_key, model, *, temperature=0.3, timeout=60.0): ...
       async def complete(self, messages, *, json_mode=False, temperature=None) -> str:
           # json_mode=True → traži strogi JSON (response_format/ekvivalent)
           ...
   ```
   Pogledaj `openai_provider.py` kao referencu (retry, JSON mode, temperature za reasoning modele).

2. **Uključi u `build_client`** (`providers/__init__.py`) + dodaj env varijable/model u `config.py`
   i `.env.example`.

### 5.3 Promjena težina ili pragova ocjena

- **Težine:** `.env` → `LEXI_WEIGHT_*` (defaultovi u `config.py`, moraju zbrojiti 1.0).
- **Pragovi A–F / labeli:** `scoring.py` → `GRADE_BANDS`.

### 5.4 Nova CLI opcija

U `cli.py`: dodaj `parser.add_argument(...)` u `build_parser`, pročitaj vrijednost u `_run`,
pa je proslijedi u `evaluate(...)` (orkestracija) ili u render dio. Novu opciju dokumentiraj u README.

### 5.5 Novi test

Dodaj u `tests/` (npr. `test_<modul>.py`). Koristi `python -m pytest -q`.
Dry-run/testovi **ne smiju** ovisiti o mreži ni ključu — koristi `MockProvider`/`--dry-run`.

### 5.6 Lokalizacija / jezik

- Detekcija jezika: `extractor.detect_language` (heuristika `čćšžđ` → hr, inače en).
- Instrukcija jezika za LLM: `agents/base.build_messages` (jedno središnje mjesto).
- **Cijeli izvještaj prati jezik članka** (HR ili EN):
  - LLM sadržaj (verdict, snage, slabosti, notes i nazivi kriterija) — prompt
    lokalizira u `build_messages`.
  - Report "chrome" (naslovi, labele, tablice, "Snage/Slabosti", "strengths", ...) —
    rječnik `_L` u `report.py` (`render_markdown`), bira se prema `article.language`.
  - Nazivi/perspektive agenata — dvojezični atributi `name_hr/en`, `perspective_hr/en`
    na svakom agentu; `orchestrator` upisuje lokaliziranu verziju u `AgentVerdict`
    (pa je i JSON dosljedan na jeziku članka).
  - Ocjena label (Excellent…Poor) — `_GRADE_LABELS` u `report.py` (npr. "Vrlo dobar").
- Datumi/vrijeme: `report.format_date` / `format_datetime` (HR dugi oblik / američki);
  JSON ostaje ISO 8601.

### 5.7 Sigurnost (nova tajna / env var)

- Dodaj polje u `config.py` + placeholder u `.env.example` (`.env` je gitignored).
- **Prije svakog commit-a/pusha** pokreni: `python scripts/check_no_secrets.py`.
- Error poruke nikad ne smiju sadržavati vrijednost ključa.

---

## 6. Konvencije

- Python **3.11+**, `from __future__ import annotations`, `pathlib`, UTF-8 — cross-OS (Win/mac/Linux).
- Lint/format: **Ruff** (`ruff check . && ruff format --check .`), line length 100, E501 ignored.
- **JSON iz LLM-a se validira pydanticom** (`AgentOutput`), na neuspjeh → `LLMParseError`;
  retry u provideru; **neuspjeh jednog agenta ne ruši cijeli run** (ADR-007).
- **Nikad hardkodirati model ni ključ** — sve kroz `.env`/`config.py` (ADR-006, ADR-008).
- **Prompti:** kanonski EN nazivi kriterija u promptima; cijeli izvještaj se lokalizira na
  jezik članka pri izvršavanju (ADR-005 dopuna).
- Testovi offline, deterministički (mock), bez mreže/ključa.

---

## 7. Naredbe (brza referenca)

```bash
# pokretanje
lexi <URL>                                            # živi run (MD na stdout)
lexi <URL> --output json --out-file rezultat.json     # JSON u fajl
lexi --dry-run --fixture tests/fixtures/sample_article.html   # offline (mock)
lexi --help

# kvaliteta
python -m pytest -q                     # testovi (23)
ruff check . && ruff format --check .   # lint + format
python scripts/check_no_secrets.py      # honeypot (obavezno prije pusha)
python scripts/demo_dry.py              # regenerira examples/demo-dry.*

# CI / pre-push gate
bash scripts/check_all.sh               # pytest + ruff + format + honeypot (lokalni gate)
git config core.hooksPath .githooks     # jednom: pre-push hook pokreće check_all.sh
```

**CI/CD:** `.github/workflows/ci.yml` (GitHub Actions) pokreće iste provjere na svakom
push/PR-u na **Ubuntu** — to je automatizirani "code review" (bez zelenih provjera
PR se ne smatra čistim). Lokalni gate `scripts/check_all.sh` to zrcali prije pusha.
