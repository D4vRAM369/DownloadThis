@echo off
setlocal

set "SCRIPT=%~dp0downloadthis_modern.py"

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 not found. Install from https://python.org and re-run.
    pause
    exit /b 1
)

if not exist "%~dp0venv\Scripts\pythonw.exe" (
    python -m venv "%~dp0venv"
    if errorlevel 1 exit /b 1
    "%~dp0venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 exit /b 1
)

echo Launching DownloadThis...
start "" "%~dp0venv\Scripts\pythonw.exe" "%SCRIPT%"
