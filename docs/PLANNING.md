# PLANNING.md — Originalni plan sesije (planiranje u repou)

> Ovaj dokument je **originalni plan** napravljen na početku zadatka (planiranje uz AI,
> prije pisanja koda) — premješten iz radne sesije u repo kao dio dostave
> ("Uključi svoje planiranje u repo"). Kod se već slaže s ovim planom; faze označene
> ✅ su dovršene. Kompaktna verzija s ADR-ovima: [`PLAN.md`](../PLAN.md).

---

# Plan — Lexi AI Text Quality Evaluator (multi-agent)

## Kontekst / TL;DR
Samostalna Python CLI aplikacija koja: (1) scrape-a Lexi blog post s URL-a, (2) izvuče čisti sadržaj članka (bez navigacije/footera/cookie banner/"Pročitaj još"), (3) pokrene ≥4 AI agenata s vlastitim promptima/perspektivama koji ocjenjuju kvalitetu teksta, (4) agregira u ukupnu ocjenu + obrazloženje po agentu. Bez DB/deploya/autha (per task). Python 3.12, pip + requirements.txt (pinned), Ruff. Cross-OS (Windows/macOS/Linux).

## Ključne odluke (potvrđene s korisnikom)
- **Lokacija:** samostalan projekt na `/home/work/Projects/lexi-evaluator` — zaseban root i zaseban git repo (✅ dovršeno; premješteno iz monorepa nakon početnog postavljanja).
- **Sučelje:** CLI (argparse), `python -m lexi_evaluator <URL>`, output JSON + Markdown u stdout/fajl. Cross-OS: čist Python, pathlib, UTF-8, bez shell skripti.
- **Provider:** OpenAI default (dani ključ) + tanak apstrakcijski sloj `providers/` spreman za Anthropic/Gemini/Ollama (samo OpenAI implementiran; uz Mock provider za offline run).
- **Sigurnost ključa (KRITIČNO / honeypot):** ključ NIKAD ne pisati ni u jedan fajl repo-a. `.env` gitignored, `.env.example` placeholder. `scripts/check_no_secrets.py` scan-ira repo za `sk-proj-` pattern i fail-a. Verifikacija `git status` + grep.
- **Trošak:** ~5 LLM poziva po run-u (4 agenta + 1 sintetizator), agenti na `gpt-4.1-mini`, sintetizator na `gpt-5-mini` (env `LEXI_MODEL` / `LEXI_MODEL_SYNTH`), article truncate na `LEXI_MAX_CHARS`, HTML cache u `.cache/` (gitignored). *(Napomena: početni plan je bio `gpt-4o-mini`; nakon rasprave o novijim modelima default je podignut na `gpt-4.1-mini` + `gpt-5-mini` — razlika u trošku zanemariva, kvaliteta bolja.)*

## Arhitektura — faze (ovisnosti u zagradama)

### Faza 1 — Scaffold ✅
1. Kreirati `lexi-evaluator/` (requirements.txt pinned: httpx, beautifulsoup4, trafilatura, openai, pydantic, pydantic-settings, python-dotenv, pytest, ruff), `.env.example` (placeholder key), `.gitignore` (.env, .venv, __pycache__, .cache/), pyproject.toml (ruff config).
2. `git init` novi repo u folderu; Python venv `.venv`; pip install. ✅
3. `config.py` (pydantic-settings: OPENAI_API_KEY, LEXI_MODEL, LEXI_MODEL_SYNTH, LEXI_MAX_CHARS, agent weights). Jasan error ako ključ fali. ✅
4. `models.py` (pydantic): `Article`, `Criterion`, `AgentVerdict`, `EvaluationResult`. ✅

### Faza 2 — Scraper + ekstraktor ✅
5. `scraper.py`: async httpx fetch, custom User-Agent, timeout, redirects, HTML cache po URL hash-u (`--no-cache` opcija). ✅
6. `extractor.py`: primarno `trafilatura.extract` (WordPress-robust), fallback BeautifulSoup — `<article>` → main container; H1 naslov, H2/H3, `<p>`, blockquote, liste; izbaci nav/footer/aside/script/style/cookie kontenjere. Output `Article` (title, author, published_at, read_time, plain_text, char_count, headings). ✅

### Faza 3 — LLM provider + agenti/prompti ✅
7. `providers/base.py`: `LLMClient` (async `complete(messages, json_mode)`), `providers/openai_provider.py`: openai SDK, structured output/JSON (`response_format`), retry s backoff. `providers/mock_provider.py`: deterministički canned odgovori za `--dry-run`/testove. ✅
8. `agents/` — registar agenata; svaki agent = id, naziv, perspektiva, system prompt, rubrika, output schema. **4 agenta:**
   - `structure.py` — Struktura i tok: jasnoća, logički flow, intro→tijelo→outro, headings, prijelazi, vodi li čitatelja. ✅
   - `psychology.py` — Psihologija pisanja: konkretnost/specifičnost, benefit za čitatelja, ton, emocije, izbjegavanje generičkog, primjeri/priče, autoritet (Lexi brend). ✅
   - `rubric.py` — Kvantitativna rubrika: fiksni kriteriji (Clarity, Structure, Specificity, Reader-benefit, Tone/Voice, Readability) svaki 0-10 + kratko obrazloženje. ✅
   - `humanity.py` — Ljudski glas / anti-generic: zvuči li ljudski/autentično vs AI-generično; cliché, robotizirani izrazi (srž Lexi poruke "why writing sounds generic"). ✅
9. `docs/PROMPTS.md` — svi promptovi verbatim + razlog dizajna po agentu (srž zadatka). ✅
10. Agent output JSON: `{score 0-10, criteria[{name,score,note}], strengths[], weaknesses[], verdict}` — validacija (pydantic) + retry na parse fail. ✅

### Faza 4 — Orkestracija, scoring, report, CLI ✅
11. `orchestrator.py`: asyncio pokreni agente paralelno (gather) → opcionalni sintetizator agent (čita sve verdict-ove → finalni sud + top preporuke; `--no-synth` flag). ✅
12. `scoring.py`: kombinirana ocjena = težinski prosjek agent score-a (structure .3, rubric .3, psychology .25, humanity .15, konfigurabilno) → 0-10 mapiran na letter grade A–F + label (Excellent…Poor) s dokumentiranim pragovima. Transparentno: zašto ocjena. ✅
13. `report.py`: JSON (strukturiran, pun) + Markdown (čovjeku čitljiv, per-agent obrazloženje + ukupno). ✅
14. `cli.py` + `__main__.py`: `python -m lexi_evaluator <url> [--output json|md] [--out-file PATH] [--model NAME] [--synth-model NAME] [--agents ...] [--no-synth] [--no-cache] [--dry-run] [--fixture PATH] [--max-chars N]`. `--dry-run` = canned/mocked agent output bez ključa (za demo/CI/test). ✅

### Faza 5 — Dokumentacija ✅
15. `README.md`: run instrukcije per OS (Windows/macOS/Linux), arhitektura, odluke, sigurnost, primjer outputa. ✅
16. `PLAN.md`: plan + ADR + kako je korišten AI (planning prompti) + cost analiza. ✅
17. `docs/PROMPTS.md` (vidi korak 9). ✅

### Faza 6 — Testovi, primjer, sigurnosna verifikacija (djelomično ✅, live run ⏳)
18. `tests/fixtures/sample_article.html` — spremljeni (trimani) pravi Lexi HTML; `tests/test_extractor.py` (assert sadrži članak, NE sadrži "Kolačići"/"Pročitaj još"/footer), `tests/test_scoring.py` (matematika agregacije), `tests/test_pipeline_dry.py` (dry-run s mock LLM, bez mreže). ✅ (12 testova, zeleno)
19. `scripts/check_no_secrets.py` — honeypot scan. ✅ (PASS)
20. ⏳ Živi run: `python -m lexi_evaluator https://lexi.hr/why-writing-sounds-generic/` → commit `examples/lexi-why-writing-sounds-generic.json` + `.md` (traži ključ u `.env`).
21. Ruff check/format; pytest zelen; honeypot čist; `git status` bez `.env`. ✅ (sve osim live runa)

## Relevantni fajlovi (puni putovi — novi)
- `lexi_evaluator/scraper.py`, `extractor.py` — scraping i čišćenje sadržaja
- `lexi_evaluator/providers/{base,openai_provider,mock_provider}.py` — LLM sloj
- `lexi_evaluator/agents/{structure,psychology,rubric,humanity}.py` — agenti + prompti
- `lexi_evaluator/orchestrator.py`, `scoring.py`, `report.py`, `cli.py` — orkestracija/output
- `docs/PROMPTS.md`, `PLAN.md`, `PLANNING.md`, `README.md` — dostava "planiranja" per task
- `scripts/check_no_secrets.py` — honeypot guard

## Verifikacija
1. ✅ `cd lexi-evaluator && .venv/bin/pytest -q` — offline, zeleno (12 passed).
2. ✅ `.venv/bin/ruff check . && .venv/bin/ruff format --check .` — čisto.
3. ⏳ `.venv/bin/python -m lexi_evaluator https://lexi.hr/why-writing-sounds-generic/ --out-file examples/...` (živi, s ključem) → validan JSON + MD.
4. ✅ `.venv/bin/python -m lexi_evaluator <url> --dry-run` (ili `--fixture`) — pipeline bez ključa/mreže.
5. ✅ `python scripts/check_no_secrets.py` → 0 pronađenih; `git status --porcelain` bez `.env`.
6. ⏳ Test na 3 navedena URL-a (why-writing-sounds-generic, psiholoski-mehanizmi-iza-clickbaita, how-to-respond-to-a-negative-review) — live, nakon što je ključ u `.env`.

## Scope
- IN: scraper+extractor, 4 agenta, scoring, CLI, docs, testovi, primjer outputa, honeypot guard.
- OUT (per task, "nemoj over-engineerati"): baza, deploy, auth, web UI, dodatni provideri (samo dokumentirani seam), CI.

## Further considerations
1. ✅ Model: `gpt-4.1-mini` za agente + `gpt-5-mini` za sintetizator (konfigurabilno preko `.env`); početna preporuka `gpt-4o-mini` je zamijenjena nakon rasprave o novijim modelima.
2. ✅ Jezik outputa: ocjene strukturirane (EN nazivi kriterija), narativ (verdict/notes) na jeziku članka (HR/EN).
3. ✅ Git: samostalan repo u `lexi-evaluator/` (branch `main`), premješten iz monorepa.
