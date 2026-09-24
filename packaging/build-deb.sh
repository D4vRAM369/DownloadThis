#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building .deb (v${VERSION})"
cd "$ROOT"
bash packaging/prepare-linux.sh

command -v dpkg-deb >/dev/null 2>&1 || {
    echo "ERROR: dpkg-deb not found (install dpkg)"
    exit 1
}

PKGROOT="$(mktemp -d)/downloadthis_${VERSION}_amd64"
trap 'rm -rf "$(dirname "$PKGROOT")"' EXIT

# Directory structure
mkdir -p "$PKGROOT/DEBIAN"
mkdir -p "$PKGROOT/usr/lib/downloadthis"
mkdir -p "$PKGROOT/usr/bin"
mkdir -p "$PKGROOT/usr/share/applications"
mkdir -p "$PKGROOT/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$PKGROOT/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$PKGROOT/usr/share/metainfo"

# App files
cp -a "$ROOT/.packaging/linux/." "$PKGROOT/usr/lib/downloadthis/"
install -m755 "$ROOT/packaging/linux/launcher.sh" "$PKGROOT/usr/bin/downloadthis"
cp "$ROOT/packaging/linux/dev.d4vram.downloadthis.desktop" \
    "$PKGROOT/usr/share/applications/"
sed -i 's|^Exec=downloadthis|Exec=/usr/bin/downloadthis|' \
    "$PKGROOT/usr/share/applications/dev.d4vram.downloadthis.desktop"
cp "$ROOT/packaging/linux/dev.d4vram.downloadthis.appdata.xml" \
    "$PKGROOT/usr/share/metainfo/"
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
Architecture: amd64
Depends: python3 (>= 3.10), ffmpeg, python3-tk
Recommends: aria2
Maintainer: D4vRAM <d4vram369@github.com>
Homepage: https://github.com/D4vRAM369/downloadthis
Description: audio downloader GUI for yt-dlp
 DownloadThis Pro is a graphical interface for yt-dlp. Extract audio
 from YouTube, SoundCloud and 1000+ sites. Supports mp3, flac, opus,
 m4a and wav. Features a download queue with real-time progress bars,
 cookie support, playlist downloads, and a Windows XP / P2P retro design.
EOF

dpkg-deb --build --root-owner-group "$PKGROOT"

OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"
mv "$(dirname "$PKGROOT")/downloadthis_${VERSION}_amd64.deb" "$OUTDIR/"

echo "==> Done: $OUTDIR/"
ls -lh "$OUTDIR/"*.deb
