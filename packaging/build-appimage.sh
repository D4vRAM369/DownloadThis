#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building AppImage (v${VERSION})"

# Locate or download appimagetool
TOOL_CACHE="$ROOT/.cache"
APPIMAGETOOL="$TOOL_CACHE/appimagetool-x86_64.AppImage"

if command -v appimagetool >/dev/null 2>&1; then
    APPIMAGETOOL="$(command -v appimagetool)"
elif [ ! -f "$APPIMAGETOOL" ]; then
    echo "==> Downloading appimagetool..."
    mkdir -p "$TOOL_CACHE"
    curl -L --fail -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

APPDIR="$ROOT/.appdir"
rm -rf "$APPDIR"

# ── AppDir structure ──────────────────────────────────────────
mkdir -p "$APPDIR/usr/lib/downloadthis"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPDIR/usr/share/metainfo"

cp "$ROOT/downloadthis_modern.py" "$APPDIR/usr/lib/downloadthis/"

# AppRun entrypoint (required by appimagetool)
install -m755 "$ROOT/packaging/linux/AppRun" "$APPDIR/AppRun"

# .desktop at AppDir root (required by appimagetool)
cp "$ROOT/packaging/linux/dev.d4vram.downloadthis.desktop" \
    "$APPDIR/dev.d4vram.downloadthis.desktop"

# AppStream metadata (eliminates appimagetool warning, enables AppImageHub)
cp "$ROOT/packaging/linux/dev.d4vram.downloadthis.appdata.xml" \
    "$APPDIR/usr/share/metainfo/"

# Icon: root name must match Icon= field in .desktop (without extension)
cp "$ROOT/packaging/assets/icon.png" "$APPDIR/dev.d4vram.downloadthis.png"
cp "$ROOT/packaging/assets/icon.png" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps/dev.d4vram.downloadthis.png"

# ── Build ─────────────────────────────────────────────────────
OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"

cd "$ROOT"

# --appimage-extract-and-run avoids FUSE requirement (works in CI containers)
ARCH=x86_64 "$APPIMAGETOOL" --appimage-extract-and-run \
    "$APPDIR" "$OUTDIR/downloadthis-${VERSION}-x86_64.AppImage"

rm -rf "$APPDIR"

echo "==> Done: $OUTDIR/downloadthis-${VERSION}-x86_64.AppImage"
ls -lh "$OUTDIR/"*.AppImage 2>/dev/null || true
