#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building .deb (v${VERSION})"

command -v dpkg-buildpackage >/dev/null 2>&1 || {
    echo "ERROR: dpkg-buildpackage not found. Run: sudo apt install dpkg-dev debhelper fakeroot"
    exit 1
}

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

SRCDIR="$TMPDIR/downloadthis-${VERSION}"
mkdir -p "$SRCDIR"

cp "$ROOT/downloadthis_modern.py" "$SRCDIR/"
cp "$ROOT/LICENSE" "$SRCDIR/"
cp "$ROOT/requirements.txt" "$SRCDIR/" 2>/dev/null || true
cp -r "$ROOT/packaging" "$SRCDIR/"
cp -r "$ROOT/packaging/linux/debian" "$SRCDIR/debian"

cd "$SRCDIR"
dpkg-buildpackage -us -uc -b

OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"
find "$TMPDIR" -maxdepth 1 -name "*.deb" -exec cp {} "$OUTDIR/" \;

echo "==> Done: $OUTDIR/"
ls -lh "$OUTDIR/"*.deb 2>/dev/null || true
