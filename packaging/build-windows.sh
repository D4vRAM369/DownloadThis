#!/usr/bin/env bash
# Run from Git Bash on Windows with Python, NSIS and WiX v3 installed.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(python -c 'import ast; tree = ast.parse(open("downloadthis_modern.py", encoding="utf-8").read()); print(next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__" for t in n.targets)))')
YTDLP_VERSION=$(python -c 'import re; v = re.search(r"^yt-dlp(?:\[default\])?>=([0-9.]+)", open("requirements.txt").read(), re.M).group(1); print(".".join(f"{int(n):02d}" for n in v.split(".")))')
mkdir -p build/windows-engine dist
curl --fail --location --retry 3 "https://github.com/yt-dlp/yt-dlp/releases/download/${YTDLP_VERSION}/yt-dlp.exe" -o build/windows-engine/yt-dlp.exe
curl --fail --location --retry 3 "https://github.com/yt-dlp/yt-dlp/releases/download/${YTDLP_VERSION}/SHA2-256SUMS" -o build/windows-engine/SHA2-256SUMS
(cd build/windows-engine && grep -E '  yt-dlp\.exe$' SHA2-256SUMS | sha256sum --check --strict -)
python -m pip install -r requirements.txt pyinstaller
PROJECT_DIR=$(cygpath -w "$PWD")
python -m PyInstaller --noconfirm --clean --onedir --windowed \
  --name downloadthis --icon "$PROJECT_DIR/packaging/icon.ico" \
  --add-data "$PROJECT_DIR/packaging/assets/icon.png;." --collect-all tkinterdnd2 \
  --specpath build downloadthis_modern.py
mkdir -p dist/downloadthis/engine
cp build/windows-engine/yt-dlp.exe dist/downloadthis/engine/
cp requirements.txt dist/downloadthis/
"dist/downloadthis/engine/yt-dlp.exe" --version
makensis -DAPP_VERSION="$VERSION" packaging/windows/installer.nsi
mkdir -p build/windows-msi
APP_SOURCE=$(cygpath -w "$PWD/dist/downloadthis")
heat dir "$APP_SOURCE" -cg AppFiles -gg -scom -sreg -sfrag -srd \
  -dr INSTALLFOLDER -var var.AppSourceDir -out build/windows-msi/AppFiles.wxs
candle -arch x64 "-dVERSION=$VERSION" -dICON_ICO=packaging/icon.ico \
  "-dAppSourceDir=$APP_SOURCE" packaging/windows/installer.wxs build/windows-msi/AppFiles.wxs \
  -out 'build/windows-msi/'
light -ext WixUIExtension build/windows-msi/installer.wixobj build/windows-msi/AppFiles.wixobj \
  -out "dist/downloadthis-${VERSION}-x64.msi"
# The portable ZIP contains the same standalone runtime as both installers.
7z a "dist/downloadthis-${VERSION}-portable-win.zip" ./dist/downloadthis
