#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"

echo "========================================"
echo " DownloadThis ${VERSION} — Build All"
echo "========================================"

OK=()
FAIL=()

run_build() {
    local name="$1"
    local script="$2"
    echo ""
    echo "--- ${name} ---"
    if bash "$script"; then
        OK+=("$name")
    else
        FAIL+=("$name  (check logs above)")
    fi
}

run_build ".deb"     "$SCRIPT_DIR/build-deb.sh"
run_build "AppImage" "$SCRIPT_DIR/build-appimage.sh"
run_build "Flatpak"  "$SCRIPT_DIR/build-flatpak.sh"
run_build "RPM"      "$SCRIPT_DIR/build-rpm.sh"
run_build "Snap"     "$SCRIPT_DIR/build-snap.sh"

echo ""
echo "========================================"
printf " Results\n"
echo "========================================"
for f in "${OK[@]+"${OK[@]}"}";   do printf "  \033[32mOK\033[0m    %s\n" "$f"; done
for f in "${FAIL[@]+"${FAIL[@]}"}"; do printf "  \033[31mFAIL\033[0m  %s\n" "$f"; done
echo ""
echo "Output: $ROOT/dist/"
ls -lh "$ROOT/dist/" 2>/dev/null || echo "(no dist/ yet)"
