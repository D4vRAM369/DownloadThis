#!/usr/bin/env bash
# Shared payload: source UI + TkDnD + verified, self-contained yt-dlp engine.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/venv/bin/python}"
if [ ! -x "$PYTHON" ]; then PYTHON=python3; fi
if [ "$(uname -m)" != x86_64 ]; then
    echo "This release recipe builds Linux x86_64 only." >&2
    exit 1
fi
VERSION="$($PYTHON -c 'import re; from pathlib import Path; v=re.search(r"yt-dlp\[default\]>=(\d+)\.(\d+)\.(\d+)", Path("requirements.txt").read_text()); print("%04d.%02d.%02d" % tuple(map(int,v.groups())))')"
CACHE="$ROOT/.packaging/engine"
PAYLOAD="$ROOT/.packaging/linux"
mkdir -p "$CACHE" "$PAYLOAD/engine"
BASE="https://github.com/yt-dlp/yt-dlp/releases/download/$VERSION"
for FILE in SHA2-256SUMS yt-dlp_linux; do
    if [ ! -f "$CACHE/$FILE" ]; then
        curl --fail --location --retry 2 "$BASE/$FILE" -o "$CACHE/$FILE.part"
        mv "$CACHE/$FILE.part" "$CACHE/$FILE"
    fi
done
(cd "$CACHE" && awk '$2 == "yt-dlp_linux" {print}' SHA2-256SUMS | sha256sum --check --strict)
install -m755 "$CACHE/yt-dlp_linux" "$PAYLOAD/engine/yt-dlp"
test "$("$PAYLOAD/engine/yt-dlp" --version)" = "$VERSION"
cp "$ROOT/downloadthis_modern.py" "$ROOT/ytdlp_updater.py" "$ROOT/requirements.txt" "$ROOT/LICENSE" "$PAYLOAD/"
"$PYTHON" -c 'import shutil, sys, tkinterdnd2; from pathlib import Path; shutil.copytree(Path(tkinterdnd2.__file__).parent, Path(sys.argv[1])/"tkinterdnd2", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))' "$PAYLOAD"
echo "Linux payload ready: $PAYLOAD"
