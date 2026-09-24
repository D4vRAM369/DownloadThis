#!/bin/bash
set -euo pipefail
# Portable Linux launcher — run from the extracted directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found. Install Python 3.10+ with Tkinter and re-run."
    exit 1
fi

exec python3 "$SCRIPT_DIR/downloadthis_modern.py" "$@"
