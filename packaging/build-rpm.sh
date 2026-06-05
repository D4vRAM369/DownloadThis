#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building RPM (v${VERSION})"

command -v rpmbuild >/dev/null 2>&1 || {
    echo "ERROR: rpmbuild not found."
    echo "On Fedora/RHEL:  sudo dnf install rpm-build"
    echo "On Debian/Ubuntu: sudo apt install rpm"
    exit 1
}

RPMROOT="$ROOT/.rpmbuild"
mkdir -p "$RPMROOT"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

SRCNAME="downloadthis-${VERSION}"
SRCDIR="$(mktemp -d)/$SRCNAME"
trap 'rm -rf "$(dirname "$SRCDIR")"' EXIT

mkdir -p "$SRCDIR"
cp "$ROOT/downloadthis_modern.py" "$SRCDIR/"
cp "$ROOT/LICENSE" "$SRCDIR/"
cp -r "$ROOT/packaging" "$SRCDIR/"

tar -czf "$RPMROOT/SOURCES/${SRCNAME}.tar.gz" -C "$(dirname "$SRCDIR")" "$SRCNAME"

cp "$ROOT/packaging/linux/downloadthis.spec" "$RPMROOT/SPECS/"

rpmbuild --define "_topdir $RPMROOT" -bb "$RPMROOT/SPECS/downloadthis.spec"

OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"
find "$RPMROOT/RPMS" -name "*.rpm" -exec cp {} "$OUTDIR/" \;

echo "==> Done: $OUTDIR/"
ls -lh "$OUTDIR/"*.rpm 2>/dev/null || true
