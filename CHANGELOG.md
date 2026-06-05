# Changelog

All notable changes to DownloadThis are documented here.

## 1.0.0 - 2026-06-05

### Added

- Audio-only GUI for `yt-dlp` with a vintage XP/P2P interface.
- Download queue with per-item progress, speed and ETA.
- Browser cookies and `cookies.txt` support.
- Playlist mode with item tracking.
- Drag and drop for URLs and `.txt` URL lists.
- Anti-403 and No-DASH presets for problematic sources.
- Persistent local configuration and session logs.
- Public `unittest` suite for URL extraction, progress parsing and unsafe argument blocking.
- Basic GitHub Actions workflow for source compile and unit tests.

### Security

- Block dangerous user-provided `yt-dlp` flags such as `--exec` and `--exec=...`.

### Notes

- v1.0 is audio-only. Audio + video support is planned for a later v1.1/v1.2 cycle.
- Native packaging is present as project scaffolding, but binary releases are not validated yet.
