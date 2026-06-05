#!/bin/bash
# Portable Linux launcher — run from the extracted directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found. Install Python 3.9+ and re-run."
    exit 1
fi

echo "Installing/updating dependencies..."
python3 -m pip install --quiet --upgrade tkinterdnd2 yt-dlp 2>/dev/null || true

exec python3 "$SCRIPT_DIR/downloadthis_modern.py" "$@"
