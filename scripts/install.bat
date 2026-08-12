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
set "ROOT=%CD%"

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
if exist .env goto :profile
echo === Creating .env from .env.example ===
copy .env.example .env >nul

REM --- 4. PowerShell "lexi" shortcut (optional, non-fatal) --------------------
:profile
set "TMPPS=%TEMP%\lexi-profile-add.ps1"
>  "%TMPPS%" echo.
>> "%TMPPS%" echo function lexi {
>> "%TMPPS%" echo   $exe = "%ROOT%\.venv\Scripts\lexi.exe"
>> "%TMPPS%" echo   if (-not (Test-Path $exe)) { Write-Error "Nije pronađeno: $exe"; return }
>> "%TMPPS%" echo   ^& $exe @args
>> "%TMPPS%" echo }
powershell -NoProfile -Command "$p=$PROFILE; $d=Split-Path $p -Parent; if(-not(Test-Path $d)){New-Item -ItemType Directory -Path $d -Force|Out-Null}; if(-not(Test-Path $p)){New-Item -ItemType File -Path $p -Force|Out-Null}; $c=Get-Content -Raw $p -ErrorAction SilentlyContinue; if($c -notmatch 'function lexi'){Add-Content -Path $p -Value (Get-Content -Raw '%TMPPS%')}"
del "%TMPPS%" >nul 2>nul

REM --- 5. Windows user PATH (so `lexi` also works in cmd / Git Bash) ----------
powershell -NoProfile -Command "$dir='%ROOT%\.venv\Scripts'; $p=[Environment]::GetEnvironmentVariable('Path','User'); if(-not $p){$p=''}; if($p -split ';' -notcontains $dir){ [Environment]::SetEnvironmentVariable('Path', ($p.TrimEnd(';') + ';' + $dir), 'User'); Write-Host ('Added to user PATH: ' + $dir) } else { Write-Host ('Already in user PATH: ' + $dir) }"

:done
echo.
echo Done. In a NEW PowerShell terminal you can now just run:
echo   lexi "URL"                (funkcija 'lexi' je dodana u tvoj profil)
echo   (dodan je i u Windows user PATH, pa radi i u cmd / Git Bashu)
echo Or activate the venv and use the full command:
echo   .\.venv\Scripts\activate
echo   lexi --help
echo   lexi --dry-run --fixture tests\fixtures\sample_article.html --output md
echo   python -m pytest -q
echo Or use the full path without activating:
echo   .\.venv\Scripts\lexi.exe --help
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
