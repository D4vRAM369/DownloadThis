"""Consent-driven yt-dlp updates; call network operations from a worker thread."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


LATEST_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
RELEASE_URL = "https://github.com/yt-dlp/yt-dlp/releases/download"
TIMEOUT = 20


def managed_executable() -> Path:
    """Return a per-user location without touching the filesystem."""
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
        return (base / "DownloadThis/bin/yt-dlp.exe").absolute()
    if platform.system() == "Darwin":
        return Path.home() / "Library/Application Support/DownloadThis/bin/yt-dlp"
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    if not base.is_absolute():
        base = Path.home() / ".local/share"
    return base / "downloadthis/bin/yt-dlp"


def _asset_name():
    system, machine = platform.system(), platform.machine().lower()
    if system == "Windows" and machine in {"amd64", "x86_64"}:
        return "yt-dlp.exe"
    if system == "Linux" and machine in {"amd64", "x86_64", "aarch64", "arm64"}:
        return "yt-dlp_linux" if machine in {"amd64", "x86_64"} else "yt-dlp_linux_aarch64"
    if system == "Darwin" and machine in {"x86_64", "arm64", "aarch64"}:
        return "yt-dlp_macos"
    raise ValueError(f"Actualización no disponible para {system} ({machine}).")


def _validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc not in {
        "api.github.com", "github.com", "release-assets.githubusercontent.com",
        "objects.githubusercontent.com",
    }:
        raise ValueError("Origen de descarga no autorizado.")


class _OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url):
    _validate_url(url)
    request = Request(url, headers={"User-Agent": "DownloadThis-Updater"})
    return build_opener(_OfficialRedirects()).open(request, timeout=TIMEOUT)


def _read(url, limit):
    with _open(url) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Respuesta de actualización demasiado grande.")
    return data


def _version(command):
    result = subprocess.run(
        [str(command), "--version"], capture_output=True, text=True,
        timeout=TIMEOUT, check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.stdout.strip()


def check_for_update(current_command: str) -> dict | None:
    """Check the official stable release; never install or launch a dialog."""
    asset_name = _asset_name()
    try:
        current = _version(current_command)
    except (FileNotFoundError, subprocess.CalledProcessError):
        current = ""
    release = json.loads(_read(LATEST_URL, 4 * 1024 * 1024))
    latest = release["tag_name"]
    if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", latest):
        raise ValueError("Versión oficial no válida.")
    current_date = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})(?:\D|$)", current)
    if current_date and tuple(map(int, current_date.groups())) >= tuple(map(int, latest.split("."))):
        return None
    assets = {asset["name"]: asset["browser_download_url"] for asset in release["assets"]}
    info = {
        "current_version": current,
        "latest_version": latest,
        "asset_name": asset_name,
        "asset_url": assets[asset_name],
        "checksums_url": assets["SHA2-256SUMS"],
    }
    _validate_release(info)
    return info


def _validate_release(info):
    version = info["latest_version"]
    if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", version):
        raise ValueError("Versión oficial no válida.")
    if info["asset_name"] != _asset_name():
        raise ValueError("El ejecutable no corresponde a esta plataforma.")
    base = f"{RELEASE_URL}/{version}"
    if (info["asset_url"] != f"{base}/{info['asset_name']}"
            or info["checksums_url"] != f"{base}/SHA2-256SUMS"):
        raise ValueError("Origen de descarga no autorizado.")


def install_update(release_info: dict) -> str:
    """Install an accepted update atomically, keeping the old binary on error."""
    _validate_release(release_info)
    checksums = _read(release_info["checksums_url"], 1024 * 1024).decode("utf-8")
    expected = None
    for line in checksums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == release_info["asset_name"]:
            expected = parts[0].lower()
            break
    if expected is None or not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("No se encontró la suma SHA256 del ejecutable.")

    target = managed_executable()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".yt-dlp-", suffix=target.suffix, dir=target.parent)
    temporary = Path(name)
    try:
        digest = hashlib.sha256()
        size = 0
        with os.fdopen(fd, "wb") as output, _open(release_info["asset_url"]) as response:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 200 * 1024 * 1024:
                    raise ValueError("Ejecutable de actualización demasiado grande.")
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != expected:
            raise ValueError("La suma SHA256 no coincide; se conserva la versión anterior.")
        temporary.chmod(0o755)
        if _version(temporary) != release_info["latest_version"]:
            raise ValueError("El ejecutable descargado no devuelve la versión esperada.")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(target)
