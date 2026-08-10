# Lexi Evaluator

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

> Jezici: nazivi kriterija i sav narativ (verdict, snage, slabosti, notes) **prate jezik
> članka** (auto-detektiran, HR ili EN), bez engleskih glosa. Datumi i vrijeme u
> izvještaju lokalizirani su isto — HR oblik (npr. "24. srpnja 2025.") ili američki
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
curl -fsSL https://raw.githubusercontent.com/lexi-hr/lexi-evaluator/main/scripts/install.sh | bash
```

Skripta sama klonira repo (u `~/lexi-evaluator`), stvori `.venv`, instalira ovisnosti +
CLI i napravi `.env`. Ako je repo hostiran negdje drugdje, postavi URL prije pokretanja:

```bash
LEXI_REPO_URL="https://github.com/TVOJ-ORG/lexi-evaluator" \
  curl -fsSL https://raw.githubusercontent.com/lexi-hr/lexi-evaluator/main/scripts/install.sh | bash
```

> **Sigurnost:** `curl | bash` izvršava udaljeni skript. Prvo ga pogledaj:
> `curl -fsSL <URL>` i pregledaj izlaz prije pipanja u `bash`.
> Skripta radi i lokalno iz repoa: `bash scripts/install.sh`.

**Windows 10/11:**

```bat
scripts\install.bat
```

Skripte rade sve automatski: stvore `.venv`, instaliraju pinned ovisnosti + CLI komandu
`lexi-evaluator`, i kreiraju `.env` iz `.env.example` (samo upiši ključ).

### Ručna instalacija

```bash
cd lexi-evaluator
python3 -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt

# Instaliraj CLI kao komandu (stvara `lexi-evaluator` na sva tri OS-a)
python -m pip install -e .

# Konfiguracija (ključ se NIKAD ne commit-a)
cp .env.example .env        # Windows: copy .env.example .env
# uredi .env i upiši pravi OPENAI_API_KEY
```

> Nakon `pip install -e .` imaš **istu komandu na Linuxu, macOS-u i Windows 10/11**:
> `lexi-evaluator <URL>`. Radi iz bilo kojeg foldera jer se `.env` traži relativno na
> projektni root (ne na trenutni direktorij). Ako ne želiš instalirati, koristi
> `python -m lexi_evaluator <URL>` iz projektnog root foldera.

### Pokretanje

```bash
# Evaluacija pravog Lexi posta (ista komanda na svim OS-ovima)
lexi-evaluator "https://lexi.hr/why-writing-sounds-generic/"

# Snimi izvještaj kao Markdown i/ili JSON
lexi-evaluator <URL> --output md  --out-file examples/run.md
lexi-evaluator <URL> --output json --out-file examples/run.json

# Offline demo bez API ključa i bez mreže (mock LLM + spremljeni fixture)
lexi-evaluator --dry-run --fixture tests/fixtures/sample_article.html
# ili: python scripts/demo_dry.py

# Opcije
lexi-evaluator <URL> --agents structure,rubric   # podskup agenata
lexi-evaluator <URL> --no-synth                  # bez finalnog suda
lexi-evaluator <URL> --no-cache                  # bez cache-a HTML-a
lexi-evaluator --help                            # sve opcije
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
pyinstaller --onefile --name lexi-evaluator lexi_evaluator\__main__.py
# rezultat: dist\lexi-evaluator.exe — pokreće se kao:
#   dist\lexi-evaluator.exe <URL>
# Napomena: za ključ i dalje treba .env u radnom folderu ili OPENAI_API_KEY env varijabla.
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

```
lexi-evaluator/
  lexi_evaluator/
    cli.py            # CLI ulaz (argparse)
    config.py         # pydantic-settings (.env)
    models.py         # pydantic modeli (Article, AgentVerdict, ...)
    scraper.py        # httpx fetch + cache
    extractor.py      # trafilatura / BeautifulSoup čisti sadržaj
    scoring.py        # agregacija + letter grade
    orchestrator.py   # paralelni agenti + sintetizator
    report.py         # Markdown/JSON render
    providers/        # LLM apstrakcija (OpenAI + Mock)
    agents/           # 4 agenta + prompti
  scripts/            # check_no_secrets.py, demo_dry.py
  tests/              # pytest + fixture stvarnog Lexi HTML-a
  examples/           # primjeri outputa (committed)
  docs/PROMPTS.md     # svi promptovi verbatim + razlozi dizajna
  PLAN.md             # planiranje + arhitekturalne odluke
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

- [`examples/demo-dry.md`](examples/demo-dry.md) / `.json` — offline demo (mock LLM)
  na stvarnom Lexi članku "Why Writing Sounds Generic: The Psychology Behind It".
- [`examples/lexi-why-writing-sounds-generic.md`](examples/lexi-why-writing-sounds-generic.md)
  / `.json` — live evaluacija s pravim ključem (7.0/10, C).
- [`examples/lexi-psiholoski-mehanizmi-iza-clickbaita.md`](examples/lexi-psiholoski-mehanizmi-iza-clickbaita.md)
  / `.json` — live evaluacija (7.7/10, C).
- [`examples/lexi-how-to-respond-to-a-negative-review.md`](examples/lexi-how-to-respond-to-a-negative-review.md)
  / `.json` — live evaluacija (7.7/10, C).
