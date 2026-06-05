#!/bin/sh
VENV="/usr/lib/downloadthis/venv"
if [ -x "$VENV/bin/python3" ]; then
    exec "$VENV/bin/python3" /usr/lib/downloadthis/downloadthis_modern.py "$@"
else
    exec python3 /usr/lib/downloadthis/downloadthis_modern.py "$@"
fi
