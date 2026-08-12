# Lexi Evaluator

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Last commit](https://img.shields.io/github/last-commit/DenisSeko/text-evaluator)](https://github.com/DenisSeko/text-evaluator)

Multi-agent AI aplikacija koja procjenjuje **koliko je dobro napisan** neki tekst s
Lexi bloga (https://lexi.hr/blog/). Dobije URL, izvuče čisti sadržaj članka, pokrene
**4 neovisna AI agenta** — svaki s vlastitom perspektivom i promptom — te spoji njihove
ocjene u ukupnu ocjenu s obrazloženjem po agentu.

> Stack: Python 3.12 · CLI · OpenAI (s apstrakcijskim slojem za druge providere)
> Bez baze, bez deploya, bez autentikacije — fokus na promptovima i orkestraciji.

---

## Kako radi

```
URL ──► scraper ──► ekstraktor ──► 4 agenta (paralelno) ──► sintetizator ──► izvještaj
              (httpx)   (trafilatura/     (OpenAI, JSON)     (finalni sud)   (MD + JSON)
                        BeautifulSoup)
```

1. **Scraping** — `scraper.py` dohvati HTML (httpx, vlastiti `User-Agent`, on-disk cache).
2. **Ekstrakcija** — `extractor.py` izvuče čisti sadržaj članka (naslov, autor, datum,
   headings, paragrafe) i odbaci navigaciju, footer, cookie banner i "Pročitaj još".
   Primarno `trafilatura`, fallback `BeautifulSoup`.
3. **Agenti** — 4 neovisna agenta, svaki s vlastitim system promptom, rubrikom i JSON
   schemom, pokrenuta paralelno (`asyncio.gather`). Vidi [docs/PROMPTS.md](docs/PROMPTS.md).
4. **Sintetizator** — 1 dodatni poziv koji pročita sve verdict-ove i napiše finalni,
   uravnotežen sud s prioritiziranim preporukama (opcionalno, `--no-synth`).
5. **Ocjenjivanje** — ukupna ocjena = težinski prosjek agent ocjena, mapirana na
   letter grade A–F + label. Vidi [Sustav ocjenjivanja](#sustav-ocjenjivanja).

### Agenti

| Agent | Perspektiva | Kriteriji |
|---|---|---|
| **Struktura i tok** | Vodi li tekst čitatelja logično kroz sadržaj | Hook, Logical flow, Heading structure, Clarity, Pacing |
| **Psihologija pisanja** | Psihološki principi dobrog pisanja | Concreteness, Reader benefit, Tone, Anti-filler, Examples, Trust |
| **Kvantitativna rubrika** | Fiksna rubrika, konzistentna ocjena | Clarity, Structure, Specificity, Reader-benefit, Tone, Readability |
| **Ljudski glas / anti-generic** | Zvuči li ljudski ili AI-generično | Authenticity, Anti-cliché, Personal voice, AI-markers |

> Jezici: **cijeli izvještaj** — od naslova i labela do naziva kriterija, verdict-a,
> snaga, slabosti i notes-a — prati auto-detektirani jezik članka (HR ili EN), bez
> engleskih glosa. To vrijedi i za JSON (imena agenata, kriterija) i za Markdown
> (uključujući "chrome" — naslove tablica, Snage/Slabosti, labele). Datumi i vrijeme
> su lokalizirani isto — HR oblik (npr. "24. srpnja 2025.") ili američki
> ("July 24, 2025"); JSON ostaje ISO 8601.

### Sustav ocjenjivanja

- Svaki agent vraća ocjenu **0–10** + kriterije + snage/slabosti + obrazloženje.
- **Ukupna ocjena** = težinski prosjek: struktura **30%**, rubrika **30%**,
  psihologija **25%**, humanost **15%** (konfigurabilno preko `.env`).
- Ako agent ne uspije, isključi se i težine se renormaliziraju (ne ruši cijeli rezultat).
- Letter grade + label:

| Ocjena | Grade | Label |
|---|---|---|
| 9.0–10 | A | Excellent |
| 8.0–8.9 | B | Very good |
| 7.0–7.9 | C | Good |
| 6.0–6.9 | D | Adequate |
| 5.0–5.9 | E | Weak |
| 0–4.9 | F | Poor |

---

## Instalacija i pokretanje (Windows / macOS / Linux)

### Preduvjet: Python 3.11+

- **Windows 10/11:** [python.org/downloads/windows](https://www.python.org/downloads/windows/)
  — pri instalaciji označi **"Add Python to PATH"**.
- **macOS:** [python.org/downloads/macos](https://www.python.org/downloads/macos/)
- **Linux:** [python.org/downloads](https://www.python.org/downloads/) ili paketni menadžer
  (`sudo apt install python3 python3-venv python3-pip` na Debian/Ubuntu).

### Brza instalacija

**Linux / macOS — direktno kroz terminal (curl, bez ručnog kloniranja):**

```bash
curl -fsSL https://raw.githubusercontent.com/DenisSeko/text-evaluator/main/scripts/install.sh | bash
```

Skripta sama klonira repo (u `~/lexi`), stvori `.venv`, instalira ovisnosti +
CLI i napravi `.env`. Ako je repo hostiran negdje drugdje, postavi URL prije pokretanja:

```bash
LEXI_REPO_URL="https://github.com/TVOJ-ORG/lexi" \
  curl -fsSL https://raw.githubusercontent.com/DenisSeko/text-evaluator/main/scripts/install.sh | bash
```

> **Sigurnost:** `curl | bash` izvršava udaljeni skript. Prvo ga pogledaj:
> `curl -fsSL <URL>` i pregledaj izlaz prije pipanja u `bash`.
> Skripta radi i lokalno iz repoa: `bash scripts/install.sh`.

**Windows 10/11** (iz projektnog root foldera):

```bat
:: cmd:          scripts\install.bat
:: PowerShell:   .\scripts\install.bat
```

> Napomena (PowerShell): skripte se ne pokreću iz trenutnog foldera bez prefiksa `.\`.
> Ako si već unutar `scripts\` foldera, pokreni `.\install.bat`.

> `install.bat` automatski dodaje PowerShell funkciju **`lexi`** u tvoj profil
> (`$PROFILE`), pa u novom terminalu možeš odmah koristiti `lexi "URL"` — bez aktivacije
> i bez pune putanje.

**Aktivacija venv-a u PowerShellu** (nakon `install.bat`, venv nije aktivan):

```powershell
# PowerShell moze blokirati .ps1 aktivaciju zbog execution policy — dopusti za sesiju:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
lexi --help
```

Ili preskoči aktivaciju i koristi punu putanju:

```powershell
.\.venv\Scripts\lexi.exe --help
```

Skripte rade sve automatski: stvore `.venv`, instaliraju pinned ovisnosti + CLI komandu
`lexi`, i kreiraju `.env` iz `.env.example` (samo upiši ključ).

### Ručna instalacija

```bash
cd lexi
python3 -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt

# Instaliraj CLI kao komandu (stvara `lexi` na sva tri OS-a)
python -m pip install -e .

# Konfiguracija (ključ se NIKAD ne commit-a)
cp .env.example .env        # Windows: copy .env.example .env
# uredi .env i upiši pravi OPENAI_API_KEY
```

> Nakon `pip install -e .` imaš **istu komandu na Linuxu, macOS-u i Windows 10/11**:
> `lexi <URL>`. Radi iz bilo kojeg foldera jer se `.env` traži relativno na
> projektni root (ne na trenutni direktorij). Ako ne želiš instalirati, koristi
> `python -m lexi_evaluator <URL>` iz projektnog root foldera.

### Pokretanje

```bash
# Evaluacija pravog Lexi posta (ista komanda na svim OS-ovima)
lexi "https://lexi.hr/why-writing-sounds-generic/"

# Snimi izvještaj kao Markdown i/ili JSON
lexi <URL> --output md  --out-file examples/run.md
lexi <URL> --output json --out-file examples/run.json

# Offline demo bez API ključa i bez mreže (mock LLM + spremljeni fixture)
lexi --dry-run --fixture tests/fixtures/sample_article.html
# ili: python scripts/demo_dry.py

# Opcije
lexi <URL> --agents structure,rubric   # podskup agenata
lexi <URL> --no-synth                  # bez finalnog suda
lexi <URL> --no-cache                  # bez cache-a HTML-a
lexi --help                            # sve opcije
```

> **Napomena o testiranju:** `--fixture` očekuje putanju do HTML fajla, a `--dry-run`
> je zasebna zastavica — obavezno oboje: `--dry-run --fixture <path>`.

### Testovi i lint

Pokreće se iz **projektnog root foldera** (`python -m` dodaje root na `sys.path`,
pa je paket importabilan):

```bash
python -m pytest -q          # offline: ekstraktor, scoring, dry-run pipeline
python scripts/check_no_secrets.py   # honeypot: provjera da nema ključeva u repou
ruff check . && ruff format --check .
```

### (Opcionalno) Samostalni `.exe` (Windows 10/11)

Ako želiš distribuirati **samostalni `.exe` bez Python instalacije**, napravi ga na
Windowsu (PyInstaller ne podržava cross-compile, pa se ne može graditi s Linuxa/macOS-a):

```powershell
.venv\Scripts\activate
python -m pip install pyinstaller
pyinstaller --onefile --name lexi lexi_evaluator\\__main__.py
# rezultat: dist\\lexi.exe — pokreće se kao:
#   dist\\lexi.exe <URL>
# Napomena: za ključ i dalje treba .env u radnom folderu ili OPENAI_API_KEY env varijabla.
```

### CI/CD i provjere prije pusha

Repo ima **automatizirani "code review" gate**:

- **GitHub Actions** (`.github/workflows/ci.yml`) — na svaki `push` na `main` i na svaki
  **pull request** automatski provjerava na **Ubuntu** (besplatni runner):
  `pytest` (offline, bez ključa/mreže), `ruff check`, `ruff format --check` i honeypot scan.
  Bez zelenih provjera PR se ne može "reviewati" kao čist.

> **Status:** workflow je **pripremljen i spreman** — automatski se pokreće na `push`/PR.
> Trenutno ne starta jer je GitHub račun zaključan zbog billinga; nakon rješavanja
> (https://github.com/settings/billing) pokreni "Re-run" ili napravi novi push.
- **Lokalni gate prije pusha** — pokreni prije `git push`:
  ```bash
  bash scripts/check_all.sh     # pytest + ruff + format + honeypot
  ```
- **Pre-push git hook** (opcionalno, automatski pokreće gate prije svakog pusha):
  ```bash
  git config core.hooksPath .githooks
  ```

---

## Konfiguracija (`.env`)

| Varijabla | Default | Opis |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI ključ (iz env varijable, nikad u kodu/repou) |
| `LEXI_MODEL` | `gpt-4.1-mini` | Model za 4 agenta (jeftin, dobar JSON) |
| `LEXI_MODEL_SYNTH` | `gpt-5-mini` | Model za sintetizator (1 poziv po run-u) |
| `LEXI_MAX_CHARS` | `40000` | Truncate članka poslanog agentima |
| `LEXI_TEMPERATURE` | `0.3` | Sampling temperatura (niska = konzistentnije) |
| `LEXI_WEIGHT_*` | vidi gore | Težine po agentu (zbroj = 1.0) |
| `LEXI_CACHE_DIR` | `.cache` | Cache raw HTML (gitignored) |

---

## Sigurnost ključa (VAŽNO)

- Ključ se učitava isključivo iz **environment varijable** ili gitignoriranog `.env`.
- `.env` je u `.gitignore`; u repo ide samo `.env.example` s placeholderom.
- `scripts/check_no_secrets.py` scan-ira repo na `sk-proj-…` i slične pattern-e i
  fail-a ako nađe bilo što — pokreni prije svakog commit-a/pusha.
- **Nikada ne commit-aj `.env` ni ključ.** Ako se to dogodi, ključ se smatra
  kompromitiranim.

---

## Projektna struktura

> Detaljan vodič za razvoj (stablo s objašnjenjima, "gdje je što", recepti za dodavanje
> agenata/providera, konvencije): [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

```
lexi/
  lexi_evaluator/
    cli.py            # CLI ulaz (argparse) + tok run-a
    config.py         # pydantic-settings (.env, projekt-relative)
    models.py         # pydantic modeli (Article, AgentVerdict, EvaluationResult, ...)
    scraper.py        # httpx fetch + cache
    extractor.py      # trafilatura / BeautifulSoup čisti sadržaj + detect_language
    scoring.py        # agregacija + letter grade + renormalizacija
    orchestrator.py   # paralelni agenti + sintetizator
    report.py         # Markdown/JSON render (+ lokalizacija datuma)
    providers/        # LLM apstrakcija (OpenAI + Mock) + build_client
    agents/           # 4 agenta (prompt + schema) + registar
  scripts/
    install.sh        # instalacija Linux/macOS (i curl | bash)
    install.bat       # instalacija Windows 10/11
    check_no_secrets.py  # honeypot scan
    demo_dry.py       # offline demo → examples/
  tests/              # pytest (ekstraktor, scoring, report, dry-run pipeline) + fixture
  examples/           # živi izvještaji s realnih Lexi postova (JSON + MD) + .gitkeep
  docs/
    PROMPTS.md        # svi promptovi verbatim + razlozi dizajna
    PLANNING.md       # originalni plan sesije
    DEVELOPMENT.md    # vodič za razvoj (gdje/kako/što)
  PLAN.md             # planiranje + arhitekturalne odluke (ADR)
  .github/workflows/ci.yml   # CI gate (pytest + ruff + honeypot)
  .githooks/                 # pre-push hook (opcionalno)
```

## Odluke (ukratko)

Detaljno u [PLAN.md](PLAN.md). Ključno:

- **CLI, ne web** — task traži "bez over-engineeringa" (bez baze/deploya/autha).
- **Python 3.12 + pip + pinned requirements** — cross-OS (Windows/macOS/Linux), bez shell skripti.
- **`gpt-4.1-mini` za agente + `gpt-5-mini` za sintetizator** — bolji omjer cijene i
  kvalitete od starijeg `gpt-4o-mini`; razlika u apsolutnom trošku je zanemariva
  (par centi po run-u). Model je lako zamijeniti preko `.env`.
- **4 perspektive, ne 3** — dodan "Ljudski glas / anti-generic" jer je to srž Lexi brenda.
- **Sintetizator kao 5. poziv** — demonstrira suradnju agenata; deterministički zbroj
  daje broj, sintetizator daje narativ (opcionalno).

---

## Primjeri outputa

Folder `examples/` sadrži **žive izvještaje s realnih Lexi postova** (dio ovog repoa),
dok se `demo-dry.*` (mock, bez ključa/mreže) generira lokalno i ne commit-a:

- **Živi run** (komitano u repou), recimo:
  - `examples/lexi-why-writing-sounds-generic.{md,json}` → **6.7/10, D (Adequate)**
  - `examples/lexi-psiholoski-mehanizmi-iza-clickbaita.{md,json}` → **7.7/10, C (Good)**
  - `examples/lexi-how-to-respond-to-a-negative-review.{md,json}` → **7.7/10, C (Good)**
- **Offline demo** (mock, bez ključa/mreže): `python scripts/demo_dry.py`
  → stvara lokalno `examples/demo-dry.{md,json}` (igitnovan)
- Novi živi run za vlastiti test: `lexi <URL> --output md --out-file examples/run.md`
  (i `--output json --out-file examples/run.json`)
