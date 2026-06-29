@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
set "APP_NAME=ChameleonLens"
set "ENTRY=main.py"
set "ENTRY_STEM=main"
set "ICON=assets\chameleon.ico"
set "LOGO=assets\chameleon_logo.png"
set "DIST_DIR=dist"
set "APP_VERSION="
set "BUILD_TIME="
set "OUTPUT_NAME="

if not exist "%VENV_PY%" (
    echo [Chameleon Lens] Initializing .venv...
    call run.bat --check-only
    if errorlevel 1 exit /b %ERRORLEVEL%
)

"%VENV_PY%" bootstrap.py --check-only
if errorlevel 1 exit /b %ERRORLEVEL%

"%VENV_PY%" -c "from chameleon_lens import __version__; print(__version__)" > "%TEMP%\chameleon_lens_version.txt"
if errorlevel 1 exit /b %ERRORLEVEL%
set /p APP_VERSION=<"%TEMP%\chameleon_lens_version.txt"
del "%TEMP%\chameleon_lens_version.txt" >nul 2>nul
if not defined APP_VERSION (
    echo [Chameleon Lens] Failed to read app version.
    exit /b 1
)

for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "Get-Date -Format HHmm"`) do set "BUILD_TIME=%%T"
if not defined BUILD_TIME (
    echo [Chameleon Lens] Failed to read build time.
    exit /b 1
)

set "OUTPUT_NAME=%APP_NAME%_%APP_VERSION%_%BUILD_TIME%.exe"

if /i "%~1"=="--print-name" (
    echo %OUTPUT_NAME%
    exit /b 0
)

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

if not exist "%LOGO%" (
    echo [Chameleon Lens] Generating menu logo...
    "%VENV_PY%" tools\generate_app_icon.py
    if errorlevel 1 exit /b %ERRORLEVEL%
)

if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"

echo [Chameleon Lens] Building %OUTPUT_NAME% with Nuitka...
"%VENV_PY%" -m nuitka --standalone --onefile --assume-yes-for-downloads --enable-plugin=pyqt5 --windows-console-mode=disable --windows-icon-from-ico="%ICON%" --include-data-files="%ICON%=assets/chameleon.ico" --include-data-files="%LOGO%=assets/chameleon_logo.png" --output-dir="%DIST_DIR%" --output-filename="%OUTPUT_NAME%" "%ENTRY%"

if errorlevel 1 exit /b %ERRORLEVEL%

for %%D in ("%DIST_DIR%\%ENTRY_STEM%.build" "%DIST_DIR%\%ENTRY_STEM%.dist" "%DIST_DIR%\%ENTRY_STEM%.onefile-build") do (
    if exist "%%~D" rmdir /s /q "%%~D"
)

echo [Chameleon Lens] Build complete: %DIST_DIR%\%OUTPUT_NAME%
exit /b 0
