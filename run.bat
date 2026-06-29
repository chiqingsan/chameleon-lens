@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
set "REQ_FILE=requirements.txt"
set "REQ_STAMP=.venv\.requirements.stamp"

if /i "%~1"=="--check-only" goto bootstrap

if exist "%VENV_PY%" if exist "%REQ_STAMP%" (
    call :requirements_hash
    if defined REQ_HASH (
        set /p STAMP_HASH=<"%REQ_STAMP%"
        if /i "!REQ_HASH!"=="!STAMP_HASH!" (
            "%VENV_PY%" -m chameleon_lens %*
            exit /b !ERRORLEVEL!
        )
    )
)

:bootstrap
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 bootstrap.py %*
exit /b %ERRORLEVEL%

:use_python
where python >nul 2>nul
if errorlevel 1 goto no_python
python bootstrap.py %*
exit /b %ERRORLEVEL%

:no_python
echo [ERROR] Python was not found. Please install Python 3.11+ and enable PATH.
pause
exit /b 1

:requirements_hash
set "REQ_HASH="
for /f "usebackq tokens=* delims=" %%H in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-FileHash -LiteralPath '%REQ_FILE%' -Algorithm SHA256).Hash.ToLowerInvariant()" 2^>nul`) do (
    if not defined REQ_HASH set "REQ_HASH=%%H"
)
set "REQ_HASH=%REQ_HASH: =%"
exit /b 0
