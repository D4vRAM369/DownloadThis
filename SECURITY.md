# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x | Yes |

## Reporting a Vulnerability

Please report security issues privately by opening a GitHub issue with minimal public detail and asking for a private contact channel.

Do not include cookies, tokens, account data, private URLs, or downloaded media in public reports.

## Scope

Security-sensitive areas include:

- user-provided `yt-dlp` extra arguments
- cookies and browser-session handling
- filesystem write paths
- subprocess execution
- packaging and installer scripts

## Current Protections

- DownloadThis passes subprocess arguments as a list and does not use `shell=True`.
- Dangerous `yt-dlp` flags that can execute commands or read host-controlled input are blocked in `extra_args`.
- Cookies are used locally and are not uploaded by the application.

## Known Limitations

- `extra_args` is protected with a denylist, not a strict allowlist.
- Native installers are not yet validated as final binary releases.
- Users are responsible for keeping `yt-dlp` and `ffmpeg` updated.
