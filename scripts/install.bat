@echo off
REM Lexi Evaluator - install script (Windows 10/11).
REM Does everything automatically:
REM   1. finds Python 3.11+
REM   2. creates a .venv
REM   3. installs pinned requirements (incl. dev/test tools) + the CLI command
REM   4. creates .env from .env.example (you only add your OPENAI_API_KEY)
REM
REM Usage:  .\scripts\install.bat   (PowerShell)  or  double-click

setlocal
cd /d "%~dp0.."

echo === Lexi Evaluator install (Windows) ===

REM --- 1. find Python --------------------------------------------------------
set "PY="
where py >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if defined PY goto :checkver
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if not defined PY goto :nopython

REM test that python is a real interpreter and not the Microsoft Store stub
%PY% -c "import sys" >nul 2>nul
if errorlevel 1 set "PY="

:checkver
if not defined PY goto :nopython
%PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto :oldpython

REM --- 2. venv ---------------------------------------------------------------
if exist .venv goto :deps
echo === Creating .venv ===
%PY% -m venv .venv

:deps
call .venv\Scripts\activate.bat
echo === Installing pinned requirements ===
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .

REM --- 3. .env ---------------------------------------------------------------
if exist .env goto :done
echo === Creating .env from .env.example ===
copy .env.example .env >nul

:done
echo.
echo Done. Quick checks:
echo   lexi-evaluator --help
echo   lexi-evaluator --dry-run --fixture tests\fixtures\sample_article.html --output md
echo   python -m pytest -q
echo Next: edit .env and set OPENAI_API_KEY (it is never committed).
endlocal
exit /b 0

:nopython
echo.
echo error: Python 3.11+ is required but was not found.
echo        This machine has no real Python, or only the Microsoft Store
echo        app execution alias, which is not real Python.
echo.
echo Fix: install Python from https://www.python.org/downloads/windows/
echo      and during install tick:
echo        - "Add Python to PATH"
echo        - keep the py launcher enabled
echo      Then close and reopen the terminal and run the installer again.
echo.
pause
exit /b 1

:oldpython
echo.
echo error: need Python 3.11+ (found: %PY%).
echo        Download: https://www.python.org/downloads/windows/
echo.
pause
exit /b 1
