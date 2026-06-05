#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building .deb (v${VERSION})"

command -v dpkg-deb >/dev/null 2>&1 || {
    echo "ERROR: dpkg-deb not found (install dpkg)"
    exit 1
}

PKGROOT="$(mktemp -d)/downloadthis_${VERSION}_all"
trap 'rm -rf "$(dirname "$PKGROOT")"' EXIT

# Directory structure
mkdir -p "$PKGROOT/DEBIAN"
mkdir -p "$PKGROOT/usr/lib/downloadthis"
mkdir -p "$PKGROOT/usr/bin"
mkdir -p "$PKGROOT/usr/share/applications"
mkdir -p "$PKGROOT/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$PKGROOT/usr/share/icons/hicolor/128x128/apps"

# App files
cp "$ROOT/downloadthis_modern.py" "$PKGROOT/usr/lib/downloadthis/"
install -m755 "$ROOT/packaging/linux/launcher.sh" "$PKGROOT/usr/bin/downloadthis"
cp "$ROOT/packaging/linux/dev.d4vram.downloadthis.desktop" \
    "$PKGROOT/usr/share/applications/"
cp "$ROOT/packaging/assets/icon.png" \
    "$PKGROOT/usr/share/icons/hicolor/256x256/apps/dev.d4vram.downloadthis.png"
cp "$ROOT/packaging/assets/icon128x128.png" \
    "$PKGROOT/usr/share/icons/hicolor/128x128/apps/dev.d4vram.downloadthis.png"

# DEBIAN/control
cat > "$PKGROOT/DEBIAN/control" << EOF
Package: downloadthis
Version: ${VERSION}-1
Section: net
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-pip, ffmpeg, python3-tk, python3-venv
Recommends: aria2
Maintainer: D4vRAM <d4vram369@github.com>
Homepage: https://github.com/D4vRAM369/downloadthis
Description: audio downloader GUI for yt-dlp
 DownloadThis Pro is a graphical interface for yt-dlp. Extract audio
 from YouTube, SoundCloud and 1000+ sites. Supports mp3, flac, opus,
 m4a and wav. Features a download queue with real-time progress bars,
 cookie support, playlist downloads, and a Windows XP / P2P retro design.
EOF

# DEBIAN/postinst — create venv and pip install deps
cat > "$PKGROOT/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
python3 -m venv /usr/lib/downloadthis/venv 2>/dev/null || true
/usr/lib/downloadthis/venv/bin/pip install --quiet tkinterdnd2 yt-dlp 2>/dev/null || true
EOF
chmod 755 "$PKGROOT/DEBIAN/postinst"

# DEBIAN/prerm — remove venv on uninstall
cat > "$PKGROOT/DEBIAN/prerm" << 'EOF'
#!/bin/sh
if [ "$1" = "remove" ]; then
    rm -rf /usr/lib/downloadthis/venv
fi
EOF
chmod 755 "$PKGROOT/DEBIAN/prerm"

dpkg-deb --build --root-owner-group "$PKGROOT"

OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"
mv "$(dirname "$PKGROOT")/downloadthis_${VERSION}_all.deb" "$OUTDIR/"

echo "==> Done: $OUTDIR/"
ls -lh "$OUTDIR/"*.deb
