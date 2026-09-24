#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building Portable archives (v${VERSION})"

cd "$ROOT"
bash packaging/prepare-linux.sh

OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"

TMPDIR="$(mktemp -d)"
PORTDIR="$TMPDIR/DownloadThis-${VERSION}-portable"
mkdir -p "$PORTDIR"

# App files and the verified Linux engine
cp -a "$ROOT/.packaging/linux/." "$PORTDIR/"
cp "$ROOT/packaging/windows/portableapp.sh" "$PORTDIR/run.sh"
chmod +x "$PORTDIR/run.sh"

cat > "$PORTDIR/README.txt" << 'EOF'
DownloadThis Portable
=====================

Requirements: Python 3.10+, Tkinter, ffmpeg, Linux x86_64

Linux:
  chmod +x run.sh && ./run.sh

The official yt-dlp engine and TkDnD are included.
The app checks for engine updates in the background and asks before installing.
EOF

# Linux tarball
tar -czf "$OUTDIR/downloadthis-${VERSION}-portable.tar.gz" \
    -C "$TMPDIR" "DownloadThis-${VERSION}-portable"
echo "  Linux:   dist/downloadthis-${VERSION}-portable.tar.gz"

rm -rf "$TMPDIR"

echo "==> Done: $OUTDIR/"
ls -lh "$OUTDIR/"*portable* 2>/dev/null || true
