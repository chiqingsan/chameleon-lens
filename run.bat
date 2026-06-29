@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
set "REQ_STAMP=.venv\.requirements.stamp"

if /i "%~1"=="--check-only" goto bootstrap

if exist "%VENV_PY%" if exist "%REQ_STAMP%" (
    "%VENV_PY%" -m chameleon_lens %*
    exit /b !ERRORLEVEL!
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
