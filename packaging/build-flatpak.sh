#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -oP "(?<=__version__ = ['\"])[^'\"]*" "$ROOT/downloadthis_modern.py" | head -1)"
echo "==> Building Flatpak (v${VERSION})"

command -v flatpak-builder >/dev/null 2>&1 || {
    echo "ERROR: flatpak-builder not found."
    echo "Run: sudo apt install flatpak flatpak-builder"
    echo "Then: flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo"
    echo "      flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47"
    exit 1
}

ensure_appstream_compose() {
    command -v appstream-compose >/dev/null 2>&1 && return 0

    local tool_dir="$ROOT/.flatpak-tools/bin"
    mkdir -p "$tool_dir"

    if [ -x /usr/libexec/appstreamcli-compose ]; then
        cat > "$tool_dir/appstream-compose" << 'EOF'
#!/usr/bin/env bash
exec /usr/libexec/appstreamcli-compose "$@"
EOF
        chmod +x "$tool_dir/appstream-compose"
        export PATH="$tool_dir:$PATH"
        return 0
    fi

    if command -v appstreamcli >/dev/null 2>&1; then
        cat > "$tool_dir/appstream-compose" << 'EOF'
#!/usr/bin/env bash
exec appstreamcli compose "$@"
EOF
        chmod +x "$tool_dir/appstream-compose"
        export PATH="$tool_dir:$PATH"
        return 0
    fi

    echo "ERROR: appstream-compose not found."
    echo "Run: sudo apt install appstream-compose appstream"
    exit 1
}

ensure_appstream_compose

# Ensure flathub remote and required runtimes
flatpak remote-add --user --if-not-exists flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true
flatpak install --user --noninteractive --or-update flathub \
    org.freedesktop.Platform//24.08 \
    org.freedesktop.Sdk//24.08

MANIFEST="$ROOT/packaging/linux/dev.d4vram.downloadthis.yaml"
BUILDDIR="$ROOT/.flatpak-builder/build"
REPODIR="$ROOT/.flatpak-builder/repo"
OUTDIR="$ROOT/dist"
mkdir -p "$OUTDIR"

cd "$ROOT"

flatpak-builder --force-clean --repo="$REPODIR" "$BUILDDIR" "$MANIFEST"
flatpak build-bundle "$REPODIR" "$OUTDIR/downloadthis-${VERSION}.flatpak" dev.d4vram.downloadthis

echo "==> Done: $OUTDIR/downloadthis-${VERSION}.flatpak"
ls -lh "$OUTDIR/"*.flatpak 2>/dev/null || true
