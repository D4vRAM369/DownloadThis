#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building Portable archives (v${VERSION})"

OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"

TMPDIR="$(mktemp -d)"
PORTDIR="$TMPDIR/DownloadThis-${VERSION}-portable"
mkdir -p "$PORTDIR"

# App files
cp "$ROOT/downloadthis_modern.py"           "$PORTDIR/"
cp "$ROOT/requirements.txt"                 "$PORTDIR/"
cp "$ROOT/packaging/windows/portableapp.bat" "$PORTDIR/run.bat"
cp "$ROOT/packaging/windows/portableapp.sh"  "$PORTDIR/run.sh"
chmod +x "$PORTDIR/run.sh"

cat > "$PORTDIR/README.txt" << 'EOF'
DownloadThis Portable
=====================

Requirements:  Python 3.9+, ffmpeg

Linux:
  chmod +x run.sh && ./run.sh

Windows:
  Double-click run.bat
  (Python must be in PATH)

First run installs tkinterdnd2 and yt-dlp via pip.
EOF

# Linux tarball
tar -czf "$OUTDIR/downloadthis-${VERSION}-portable.tar.gz" \
    -C "$TMPDIR" "DownloadThis-${VERSION}-portable"
echo "  Linux:   dist/downloadthis-${VERSION}-portable.tar.gz"

# Windows zip (same content, zip format)
if command -v zip >/dev/null 2>&1; then
    (cd "$TMPDIR" && zip -qr "$OUTDIR/downloadthis-${VERSION}-portable-win.zip" \
        "DownloadThis-${VERSION}-portable")
    echo "  Windows: dist/downloadthis-${VERSION}-portable-win.zip"
fi

rm -rf "$TMPDIR"

echo "==> Done: $OUTDIR/"
ls -lh "$OUTDIR/"*portable* 2>/dev/null || true
