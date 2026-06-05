#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building Snap (v${VERSION})"

command -v snapcraft >/dev/null 2>&1 || {
    echo "ERROR: snapcraft not found."
    echo "Run: sudo snap install snapcraft --classic"
    exit 1
}

cd "$ROOT"

# snapcraft expects snapcraft.yaml at project root
cp packaging/linux/snapcraft.yaml .
trap 'rm -f snapcraft.yaml' EXIT

snapcraft --destructive-mode

OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"
find "$ROOT" -maxdepth 1 -name "*.snap" -exec mv {} "$OUTDIR/" \;

echo "==> Done: $OUTDIR/"
ls -lh "$OUTDIR/"*.snap 2>/dev/null || true
