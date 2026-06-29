@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

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
