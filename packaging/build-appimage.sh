#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building AppImage (v${VERSION})"

command -v appimage-builder >/dev/null 2>&1 || {
    echo "ERROR: appimage-builder not found. Run: pip install appimage-builder"
    exit 1
}

cd "$ROOT"

# Prepare AppDir
APPDIR="$ROOT/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib/downloadthis"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp downloadthis_modern.py "$APPDIR/usr/lib/downloadthis/"

# Install Python deps into AppDir
python3 -m pip install --quiet --target "$APPDIR/usr/local/lib/python3.10/dist-packages" \
    tkinterdnd2 yt-dlp

cp packaging/linux/dev.d4vram.downloadthis.desktop \
    "$APPDIR/usr/share/applications/"
cp packaging/icon.png \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps/dev.d4vram.downloadthis.png"

appimage-builder --recipe packaging/linux/AppImageBuilder.yml --skip-test

OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"
find "$ROOT" -maxdepth 1 -name "*.AppImage" -exec mv {} "$OUTDIR/" \;

# Cleanup
rm -rf "$APPDIR"

echo "==> Done: $OUTDIR/"
ls -lh "$OUTDIR/"*.AppImage 2>/dev/null || true
