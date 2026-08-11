@echo off
REM Lexi Evaluator - install script (Windows 10/11).
REM Does everything automatically:
REM   1. finds Python 3.11+
REM   2. creates a .venv
REM   3. installs pinned requirements (incl. dev/test tools) + the CLI command
REM   4. creates .env from .env.example (you only add your OPENAI_API_KEY)
REM
REM Usage:  scripts\install.bat   (or double-click)

setlocal
cd /d "%~dp0.."

echo === Lexi Evaluator install (Windows) ===

REM --- 1. Python -------------------------------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if defined PY (
  REM "python" na PATH-u moze biti Microsoft Store "app execution alias" (stub
  REM koji ispisuje "Python was not found..."). Provjeri radi li stvarno.
  %PY% -c "import sys" >nul 2>nul
  if errorlevel 1 set "PY="
)
if not defined PY (
  echo.
  echo error: Python 3.11+ is required but was not found.
  echo        Ovaj racun nema pravi Python (ili postoji samo Microsoft Store
  echo        "app execution alias", sto NIJE pravi Python).
  echo.
  echo Fix: instaliraj Python sa https://www.python.org/downloads/windows/
  echo      i tijekom instalacije OZNACI:
  echo        - "Add Python to PATH"
  echo        - zadrzi "py launcher" ukljucenim
  echo      Zatim ZATVORI i PONOVNO OTVORI terminal i pokreni installer opet.
  echo.
  pause
  exit /b 1
)

%PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
  echo.
  echo error: need Python 3.11+ (found: %PY%).
  echo        Download: https://www.python.org/downloads/windows/
  echo.
  pause
  exit /b 1
)

REM --- 2. venv ---------------------------------------------------------------
if not exist .venv (
  echo === Creating .venv ===
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat

REM --- 3. Dependencies + CLI -------------------------------------------------
echo === Installing pinned requirements ===
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .

REM --- 4. .env ---------------------------------------------------------------
if not exist .env (
  echo === Creating .env from .env.example ===
  copy .env.example .env >nul
)

echo.
echo Done. Quick checks:
echo   lexi-evaluator --help
echo   lexi-evaluator --dry-run --fixture tests\fixtures\sample_article.html --output md
echo   python -m pytest -q
echo Next: edit .env and set OPENAI_API_KEY (it is never committed).
endlocal
