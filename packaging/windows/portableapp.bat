@echo off
setlocal

set "SCRIPT=%~dp0downloadthis_modern.py"

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 not found. Install from https://python.org and re-run.
    pause
    exit /b 1
)

echo Installing/updating dependencies...
python -m pip install --quiet --upgrade tkinterdnd2 yt-dlp

echo Launching DownloadThis...
start "" pythonw "%SCRIPT%"
