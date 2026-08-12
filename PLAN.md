# PLAN.md — Planiranje, arhitektura i odluke

Ovaj dokument prikazuje **proces** izrade zadatka: kako je projekt planiran, koje
arhitekturalne odluke su donesene i zašto, te kako je AI korišten tijekom razvoja.

---

## 1. Što gradimo (spec)

Aplikacija procjenjuje koliko je dobro napisan neki Lexi tekst pomoću **više AI
agenata**:

- **Input:** URL Lexi blog posta ili case studyja
- **Scraping:** dohvati stranicu i izvuci čisti sadržaj posta (bez navigacije, footera i sl.)
- **Multi-agent verifikacija:** više agenata, svaki s vlastitim promptom i perspektivom,
  ocjenjuje je li tekst dobro napisan
- **Output:** ukupna ocjena + obrazloženje po agentu

Zadane granice: bez baze, bez deploya, bez autentikacije; fokus na promptovima,
orkestraciji i čistoći rješenja; nekoliko LLM poziva po pokretanju; ključ se nikad ne
smije naći u repou.

---

## 2. Ključne odluke (ADR — Architecture Decision Records)

### ADR-001: Python CLI, ne web aplikacija
**Odluka:** CLI alat pokretan s `python -m lexi_evaluator <URL>`, output u Markdown + JSON.
**Zašto:** spec izričito traži "bez over-engineeringa" (bez baze, deploya, autha). CLI je
najmanji mogući površinski dio koji čisti pipeline čini upotrebljivim i testabilnim.
Web UI (Streamlit/FastAPI) dodaje površinu bez dodatne vrijednosti za ocjenu zadatka.
**Alternativa odbačena:** FastAPI server — previše infrastrukture, a spec ne traži servis.

### ADR-002: Samostalan projekt, zaseban git repo
**Odluka:** projekt živi u vlastitom root folderu `lexi-evaluator/` s vlastitim git repoom,
van postojećeg monorepa u kojem je nastao.
**Zašto:** zadatak traži javni GitHub repo; miješanje sa servisnim monorepom (CI, docs-sync,
pnpm workspace) donosi rizike i buku. Potpuna izolacija.
**Posljedica:** vlastiti `requirements.txt`, `.venv`, `.env`, `.gitignore`.

### ADR-003: Python 3.12, pip + pinned requirements, bez shell skripti
**Odluka:** `requirements.txt` s pinned verzijama; sve se pokreće s `python -m ...`.
**Zašto:** cross-OS zahtjev (Windows/macOS/Linux). Čist Python s `pathlib` + UTF-8 radi
svugdje; `uv`/`poetry` su opcija, ali pip + pinned je najmanje ovisnosti i najpredvidljivije.
Ruff za lint/format (isti standard kao i okolina iz koje projekt potječe).
**Dopuna (iz live verifikacije):** `pyproject.toml` definira `[project.scripts]`
(`lexi-evaluator = "lexi_evaluator.cli:main"`), pa nakon `pip install -e .` postoji ista
komanda `lexi-evaluator <URL>` na sva tri OS-a (stvara `.venv/bin/lexi-evaluator` na
Linux/macOS i `.venv\Scripts\lexi-evaluator.exe` na Windowsu). `.env` se učitava relativno
na projektni root (`config.py`), ne na CWD — komanda radi iz bilo kojeg foldera.
**Convenience:** postoje opcionalne instalacijske skripte `scripts/install.sh`
(Linux/macOS) i `scripts/install.bat` (Windows) — automatiziraju venv + ovisnosti + `.env`.
One su čisti convenience; ručni koraci (u README) i dalje rade, pa "bez shell skripti"
kao princip za pokretanje aplikacije ostaje na snazi. Za distribuciju bez Python instalacije
README dokumentira opciju gradnje samostalnog `.exe`-a (PyInstaller, mora se raditi na
Windowsu — nema cross-compile-a).

### ADR-004: Scraping — trafilatura primarno, BeautifulSoup fallback
**Odluka:** `trafilatura.extract` kao primarni ekstraktor, fallback na ciljanu
BeautifulSoup ekstrakciju (`<article>`/`main`, H1–H3, `<p>`, blockquote, liste;
izbacivanje nav/footer/aside/cookie kontenjera).
**Zašto:** Lexi blog je WordPress; trafilatura je izgrađena upravo za takve stranice i
pouzdano uklanja boilerplate. Fallback osigurava rad i na neobičnim layoutima.
**Test:** fixture = stvarni Lexi HTML; testovi dokazuju da "Kolačići", "Pročitaj još",
footer i "© 2026" **ne** procuruju u članak.

### ADR-005: 4 agensa, ne minimalna 3
**Odluka:** struktura, psihologija, kvantitativna rubrika + **ljudski glas / anti-generic**.
**Zašto:** treća perspektiva je unutar speca ("Scoring: kvantitativna ocjena po kriterijima"),
ali Lexi je brend izgrađen na poruci "zašto pisanje zvuči generički" — pa je detektor
generičkog/AI pisanja i najrelevantniji. Svaki agent ima vlastiti system prompt, rubriku i
JSON schemu; pokreću se paralelno pa dodatni agent ne košta gotovo ništa u vremenu.
**Razmišljanje o promptima:** detaljno u [docs/PROMPTS.md](docs/PROMPTS.md).

### ADR-006: Modeli — `gpt-4.1-mini` za agente, `gpt-5-mini` za sintetizator
**Odluka:** default agenti = `gpt-4.1-mini`, sintetizator = `gpt-5-mini`, oba preko `.env`.
**Zašto:** početni plan je bio `gpt-4o-mini` (jeftin, pouzdan JSON), ali je taj model
zastario. Noviji modeli bitno bolje slijede prompt i vraćaju valjan JSON, a **apsolutna
razlika u trošku je zanemariva** (članci su kratki, ~5 poziva po run-u → par centi).
Sintetizator ima samo 1 poziv po run-u, pa tamo smije koštati malo više za višu kvalitetu.
Sve je konfigurabilno — kod nikad ne hardkodira model.
**Napomena o ključu:** modeli se naplaćuju po tokenu; promjena modela ne traži nikakav
dodatni setup na tvrtkinom ključu.

### ADR-007: Deterministička agregacija + narativni sintetizator
**Odluka:** ukupna ocjena = težinski prosjek agent ocjena (structure 30%, rubric 30%,
psychology 25%, humanity 15%), mapiran na A–F; finalni narativ piše sintetizator.
**Zašto:** broj mora biti ponovljiv i transparentan (svaka ocjena se može objasniti
težinama i agent score-ovima), a sintetizator dodaje ljudski čitljiv sud i prioritizirane
preporuke. To demonstrira "suradnju agenata" — 5. poziv, opcionalan (`--no-synth`).
**Robustnost:** ako jedan agent padne, isključi se i težine se renormaliziraju.

### ADR-008: Sigurnost ključa = honeypot guard
**Odluka:** ključ se čita isključivo iz env/`.env` (gitignored); `scripts/check_no_secrets.py`
scan-ira sve fajlove na `sk-proj-…`, `sk-ant-…`, AWS i generičke key pattern-e te provjerava
da nijedan `.env` nije u git indexu; exit code ≠ 0 ako nađe nešto.
**Zašto:** repo je javan; commitani ključ = diskvalifikacija. Guard je alat koji to
mehanički sprječava prije svakog pusha.
**Dodatno:** kod nikad ne logira ključ; error poruke ne sadrže vrijednost ključa.

### ADR-009: LLM apstrakcija, ali samo OpenAI implementiran
**Odluka:** tanak `LLMClient` interface + `providers/`; implementiran OpenAI + Mock.
**Zašto:** spec dozvoljava druge providere (Anthropic/Gemini/Ollama), ali traži fokus.
Interface čini pipeline agnostičnim bez dodatnog koda; dodavanje providera = jedna klasa.
Mock provider omogućuje testove i demo **bez ključa i mreže**.

---

## 3. Sustav ocjenjivanja

- Skala: **0–10** po agentu; ukupno = težinski prosjek.
- Letter grade: A ≥ 9.0, B ≥ 8.0, C ≥ 7.0, D ≥ 6.0, E ≥ 5.0, F < 5.0, s labelima
  (Excellent … Poor).
- Svaki agent vraća: `score`, `criteria[]` (name/score/note), `strengths[]`,
  `weaknesses[]`, `verdict` — pa je jasno **zašto** je tekst dobio ocjenu koju je dobio.
- **Jezik reviewa** se auto-detektira iz članka (`extractor.detect_language`: hrvatski
  dijakritici `čćšžđ` → HR, inače EN) i prosljeđuje u prompt svih agenata — **cijeli
  izvještaj** (verdict, snage, slabosti, notes i nazivi kriterija) piše se **samo na
  jeziku članka**, bez engleskih glosa u zagradi. I **report "chrome"** (naslovi, labele,
  tablice, imena agenata, labeli ocjena A–F) prati jezik članka: dvojezični nazivi
  agenata (`name_hr/en`, `perspective_hr/en`) + rječnik `_L`/`_GRADE_LABELS` u `report.py`;
  za HR članak npr. "Very good" → "Vrlo dobar".
- **Datumi i vrijeme** u izvještaju se lokaliziraju prema jeziku članka: HR dugi oblik
  ("24. srpnja 2025." / "u 22:09 (UTC)") za hrvatski, američki oblik ("July 24, 2025" /
  ", 22:09 (UTC)") za engleski (`report.format_date` / `format_datetime`; JSON ostaje
  ISO 8601 zbog strojne čitljivosti).
- JSON se validira (pydantic) i po potrebi retry-ja; na ponovljeni neuspjeh agent se
  označi kao neuspješan i ne ruši cijeli run.

## 4. Troškovi

- **~5 LLM poziva po run-u:** 4 agenta + 1 sintetizator (opcionalno).
- Lexi postovi su kratki (~450–1500 riječi); `LEXI_MAX_CHARS=40000` je gornja granica.
- S `gpt-4.1-mini` / `gpt-5-mini` trošak po evaluaciji je reda **par centi**.
- Razvoj štedi pozive: HTML cache na disku, offline `--dry-run` s mock LLM-om, testovi bez mreže.

## 5. Kako je AI korišten u planiranju i razvoju

Zadatak izričito potiče korištenje AI-ja. Proces u ovom repou:

1. **Planning prompt** (prije pisanja koda) tražio je: istražiti workspace (gdje projekt
   stane, koje su konvencije), istražiti Lexi blog strukturu, pa napraviti plan s fazama,
   odlukama, fajlovima i verifikacijom. Rezultat je ovaj `PLAN.md` + `docs/PROMPTS.md`.
2. **Odluke su dokumentirane** kao ADR-ovi (gore) — "zašto baš tako" je dio dostave.
3. **Prompti agenata** su dizajnirani kao samostalni artefakt (vidi PROMPTS.md) — to je
   srž zadatka i namjerno je odvojeno od koda da se lako čita i mijenja.
4. **Iterativna verifikacija:** pytest (offline), ruff, dry-run, honeypot — svaki korak
   je provjeren prije sljedećeg.

## 6. Verifikacija

- [x] `pytest -q` — **23 testa**, offline (ekstraktor na stvarnom fixtureu, scoring,
  report lokalizacija, dry-run pipeline) — detaljan popis u [§6.1](#61-popis-testova-detaljno)
  i u `tests/`. Pokreće se s `.venv/bin/python -m pytest -q` (ili `python -m pytest -q`
  uz aktiviran venv).
- [x] `ruff check .` + `ruff format --check .` — čisto
- [x] `python scripts/demo_dry.py` — cijeli pipeline bez ključa/mreže, generira `examples/`
- [x] `python scripts/check_no_secrets.py` — nema ključeva u repou
- [x] Live run na stvarnom Lexi postu s pravim ključem → `examples/` (ključ u `.env`)
  - 3 URL-a (JSON + MD u `examples/`): `why-writing-sounds-generic`
    (**6.7/10, D — Adequate**), `psiholoski-mehanizmi-iza-clickbaita`
    (**7.7/10, C — Good**), `how-to-respond-to-a-negative-review`
    (**7.7/10, C — Good**)
- [x] CI/CD gate: `.github/workflows/ci.yml` (GitHub Actions, Ubuntu: pytest + ruff +
  format + honeypot) + lokalna `scripts/check_all.sh` (validirana) + pre-push hook
  (`git config core.hooksPath .githooks`)

### 6.1 Popis testova (detaljno)

Pokretanje: `.venv/bin/python -m pytest -q` → **23 passed**. Svi testovi su **offline**
(mock LLM, spremljeni HTML fixture, bez mreže i bez API ključa).

**`tests/test_extractor.py` — ekstrakcija (10 testova)**
fixture = `tests/fixtures/sample_article.html` (pravi, trimani Lexi HTML).

| Test | Provjerava |
|---|---|
| `test_article_extracted` | plain_text je neprazan, riječi > 50, char_count == len(plain_text) |
| `test_title_detected` | naslov postoji i sadrži "generic" |
| `test_contains_article_body` | stvarna rečenica iz članka ("nobody wakes up"/"generic") je preživjela |
| `test_boilerplate_removed` | "kolačići", "pročitaj još", "all rights reserved", "© 2026" NE procuruju |
| `test_headings_detected` | ≥1 heading, među njima "generic" |
| `test_source_is_set` | source je "trafilatura" ili "beautifulsoup" |
| `test_article_language` | detektiran "en" (fixture je engleski članak) |
| `test_detect_language_english` | rječnik bez dijakritika → "en" |
| `test_detect_language_croatian` | rječnik s `čćšžđ` → "hr" |
| `test_detect_language_empty` | prazan string → "en" |

**`tests/test_scoring.py` — agregacija ocjena (4 testa)**

| Test | Provjerava |
|---|---|
| `test_weighted_mean` | težinski prosjek 30/30/25/15 je točan i zaokružen na 2 decimale |
| `test_failed_agent_renormalises_weights` | uspali agent (error!) se izbaci, težine se renormaliziraju 50/50 |
| `test_all_failed_gives_zero` | svi agenti uspali → 0.0 / F |
| `test_grade_bands` | mapiranje svih pragova A–F → (grade, label) |

**`tests/test_report.py` — lokalizacija datuma i report chrome-a (7 testova)**

| Test | Provjerava |
|---|---|
| `test_format_date_croatian` | "2026-01-28" + hr → "28. siječnja 2026." |
| `test_format_date_american` | "2026-01-28" + en → "January 28, 2026" |
| `test_format_datetime_croatian` | ISO + hr → "10. kolovoza 2026. u 21:02 (UTC)" |
| `test_format_datetime_american` | ISO + en → "August 10, 2026, 21:02 (UTC)" |
| `test_format_date_unknown_value_passthrough` | "n/a"/"unknown" prolazi nepromijenjeno |
| `test_report_chrome_localized_croatian` | HR članak → HR chrome: naslovi, labele, tablice, agenti ("Vrlo dobar", "Kriterij/Ocjena/Obrazloženje", "Snage/Slabosti") |
| `test_report_chrome_localized_english` | EN članak → EN chrome: "Overall score", "Criterion/Score/Rationale", "Strengths/Weaknesses"; bez hrvatskih labela |

**`tests/test_pipeline_dry.py` — end-to-end pipeline s mock LLM-om (2 testa)**

| Test | Provjerava |
|---|---|
| `test_dry_run_pipeline` | 4 verdicta bez grešaka, ocjene 0–10, kriteriji i verdict postoje, overall > 0 s validnim letter grade, sinteza postoji, **4 agent poziva + 1 sintetizator** |
| `test_dry_run_without_synthesizer` | samo 2 odabrana agenta, sinteza i synth model = None |

## 7. Napomena o modelima (iz live verifikacije)

- **`gpt-5` / o-serija modeli ne prihvaćaju custom `temperature`** (samo default 1).
  `OpenAIProvider` sada prepoznaje reasoning modele po prefiksu (`gpt-5`, `o1`, `o3`, `o4`, `o5`)
  i ne šalje `temperature`, uz sigurnosnu mrežu: ako API i dalje odbije, retry bez parametra.
  Ostali `BadRequestError`-i se pretvaraju u `LLMError` da ne sruše cijeli run
  (usklađeno s ADR-007 — neuspjeh jednog agenta se izolira).

## 8. Known limitations / future work

- Provideri: samo OpenAI implementiran; Anthropic/Gemini/Ollama zahtijevaju jednu klasu svaki.
- Ekstraktor pretpostavlja tekstualni sadržaj; video/infografika nisu evaluirani.
- Težine su fiksne (konfigurabilne); A/B kalibracija težina na većem uzorku je future work.
- Nema rate-limit/retry politike prema `lexi.hr` (samo `User-Agent` + cache) — dovoljno za demo.
