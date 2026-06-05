Name:           downloadthis
Version:        1.0.0
Release:        1%{?dist}
Summary:        Audio downloader GUI for yt-dlp with a vintage XP/P2P interface
License:        MIT
URL:            https://github.com/D4vRAM369/downloadthis
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

Requires:       python3 >= 3.9
Requires:       python3-pip
Requires:       ffmpeg
Requires:       python3-tkinter
Recommends:     aria2

%description
DownloadThis Pro is a graphical interface for yt-dlp. Extract audio
from YouTube, SoundCloud and 1000+ sites. Supports mp3, flac, opus,
m4a and wav. Features a download queue with real-time progress bars,
cookie support, playlist downloads, and a Windows XP / P2P retro design.

%prep
%setup -q

%install
install -Dm644 downloadthis_modern.py %{buildroot}/usr/lib/downloadthis/downloadthis_modern.py
install -Dm644 packaging/linux/dev.d4vram.downloadthis.desktop \
    %{buildroot}/usr/share/applications/dev.d4vram.downloadthis.desktop
install -Dm644 packaging/assets/icon.png \
    %{buildroot}/usr/share/icons/hicolor/256x256/apps/dev.d4vram.downloadthis.png
install -Dm644 LICENSE %{buildroot}/usr/share/licenses/%{name}/LICENSE

mkdir -p %{buildroot}/usr/bin
cat > %{buildroot}/usr/bin/downloadthis << 'LAUNCHER'
#!/bin/sh
VENV="/usr/lib/downloadthis/venv"
if [ -x "$VENV/bin/python3" ]; then
    exec "$VENV/bin/python3" /usr/lib/downloadthis/downloadthis_modern.py "$@"
else
    exec python3 /usr/lib/downloadthis/downloadthis_modern.py "$@"
fi
LAUNCHER
chmod 755 %{buildroot}/usr/bin/downloadthis

%post
python3 -m venv /usr/lib/downloadthis/venv 2>/dev/null || true
/usr/lib/downloadthis/venv/bin/pip install --quiet tkinterdnd2 yt-dlp 2>/dev/null || true

%preun
if [ $1 -eq 0 ]; then
    rm -rf /usr/lib/downloadthis/venv
fi

%files
/usr/lib/downloadthis/downloadthis_modern.py
/usr/bin/downloadthis
/usr/share/applications/dev.d4vram.downloadthis.desktop
/usr/share/icons/hicolor/256x256/apps/dev.d4vram.downloadthis.png
/usr/share/licenses/%{name}/LICENSE

%changelog
* Thu Jun 05 2026 D4vRAM <d4vram369@github.com> - 1.0.0-1
- Initial release
