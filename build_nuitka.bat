@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
set "APP_NAME=ChameleonLens"
set "ENTRY=main.py"
set "ENTRY_STEM=main"
set "ICON=assets\chameleon.ico"
set "DIST_DIR=dist"

if not exist "%VENV_PY%" (
    echo [Chameleon Lens] Initializing .venv...
    call run.bat --check-only
    if errorlevel 1 exit /b %ERRORLEVEL%
)

"%VENV_PY%" bootstrap.py --check-only
if errorlevel 1 exit /b %ERRORLEVEL%

"%VENV_PY%" -c "import nuitka" >nul 2>nul
if errorlevel 1 (
    echo [Chameleon Lens] Installing Nuitka build dependencies...
    "%VENV_PY%" -m pip install nuitka ordered-set zstandard
    if errorlevel 1 exit /b %ERRORLEVEL%
)

if not exist "%ICON%" (
    echo [Chameleon Lens] Generating app icon...
    "%VENV_PY%" tools\generate_app_icon.py
    if errorlevel 1 exit /b %ERRORLEVEL%
)

if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"

echo [Chameleon Lens] Building with Nuitka...
"%VENV_PY%" -m nuitka --standalone --onefile --assume-yes-for-downloads --enable-plugin=pyqt5 --windows-console-mode=disable --windows-icon-from-ico="%ICON%" --include-data-files="%ICON%=assets/chameleon.ico" --include-data-files="VERSION=VERSION" --output-dir="%DIST_DIR%" --output-filename="%APP_NAME%.exe" "%ENTRY%"

if errorlevel 1 exit /b %ERRORLEVEL%

for %%D in ("%DIST_DIR%\%ENTRY_STEM%.build" "%DIST_DIR%\%ENTRY_STEM%.dist" "%DIST_DIR%\%ENTRY_STEM%.onefile-build") do (
    if exist "%%~D" rmdir /s /q "%%~D"
)

echo [Chameleon Lens] Build complete: %DIST_DIR%\%APP_NAME%.exe
exit /b 0
