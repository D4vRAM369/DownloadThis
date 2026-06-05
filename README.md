<div align="center">

# DownloadThis Pro

**GUI para yt-dlp — extrae audio de YouTube, SoundCloud y 1000+ sitios, sin complicaciones**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)](https://python.org)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-latest-red?style=flat-square)](https://github.com/yt-dlp/yt-dlp)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows-lightgrey?style=flat-square)]()

[English version below ↓](#english)

</div>

---

## ¿Qué es esto?

DownloadThis es una interfaz gráfica para [yt-dlp](https://github.com/yt-dlp/yt-dlp) construida con Python y tkinter. La idea es sencilla: tienes URLs, quieres archivos en tu disco, sin tocar la terminal cada vez.

Sin tracking. Sin cuenta. Sin nada subido a ningún servidor. Todo corre en local.

Nació como proyecto personal porque las GUIs que existían eran o demasiado básicas o demasiado infladas. Esta hace lo que necesito, con un diseño que recuerda a los clientes P2P de los 2000s — eMule, Ares, DC++ — porque ese estilo tiene algo que las apps modernas han perdido: claridad brutal.

---

## Características

- **Cola de descargas** con barra de progreso por elemento, velocidad y ETA en tiempo real
- **Formatos**: mp3, m4a, flac, opus, wav y todo lo que soporte yt-dlp
- **Calidad configurable** (0–9 para audio)
- **Soporte de cookies** de navegador (Brave, Firefox, Chrome) para sitios con login
- **Descarga de playlists** completas con un toggle
- **Drag & drop** de URLs y archivos `.txt` con listas de enlaces
- **Anti-403** y modo **No-DASH** para sitios problemáticos con auto-fallback
- **Plantillas de nombre** de archivo personalizables (`%(title)s.%(ext)s`, etc.)
- **Registro de actividad** en tiempo real con timestamps
- **Configuración persistente** en `~/.config/downloadthis/config.json`
- **Barra de estado** con velocidad global, elementos activos y versión de yt-dlp
- **Auto-guardado de cola** al cerrar — se restaura en la siguiente sesión

---

## Requisitos

| Herramienta | Obligatorio | Instalar |
|-------------|-------------|---------|
| **Python 3.9+** | ✅ | [python.org](https://python.org) |
| **yt-dlp** | ✅ | `pip install yt-dlp` |
| **ffmpeg** | ✅ | ver abajo |
| **aria2c** | ❌ opcional | mejora velocidad multi-conexión |

```bash
# ffmpeg en Debian/Ubuntu
sudo apt install ffmpeg

# ffmpeg en Arch
sudo pacman -S ffmpeg

# ffmpeg en Windows (winget)
winget install ffmpeg

# aria2c (opcional)
sudo apt install aria2
```

---

## Instalación

```bash
# Clona el repositorio
git clone https://github.com/D4vRAM369/downloadthis.git
cd downloadthis

# Instala dependencias Python
pip install -r requirements.txt

# Lanza la app
python3 downloadthis_modern.py
```

> La primera vez que se ejecuta, instala automáticamente cualquier dependencia Python faltante.

---

## Uso rápido

```
1. Copia una URL (Ctrl+C en el navegador)
2. En la app → "📋 Pegar URL"  o Ctrl+V
3. Elige la carpeta de destino con "📁 Destino"
4. Click "▼ DESCARGAR TODO"
```

Para instrucciones completas, cookies, playlists y solución de problemas → **[USAGE_GUIDE.md](USAGE_GUIDE.md)**

---

## Estructura del proyecto

```
downloadthis/
├── downloadthis_modern.py     # App completa (~1800 líneas)
├── requirements.txt           # Dependencias pip
├── pyproject.toml             # Build metadata
├── README.md
├── USAGE_GUIDE.md             # Guía de uso paso a paso (pública)
└── ~/.config/downloadthis/    # Generado en runtime
    ├── config.json            # Config persistente
    └── logs/
        └── YYYY-MM-DD.txt     # Logs de sesión
```

---

## Distribución

Disponible directamente desde este repositorio.  
Packaging nativo para Linux (`.desktop`) y Windows (NSIS/WiX) en `packaging/`.

## Roadmap

- **v1.0**: extracción de audio local con `yt-dlp`
- **v1.1/v1.2**: modo audio + vídeo, cuando exista selector dedicado, comandos separados y tests propios

---

## Contribuir

Abre un issue si encuentras algo roto o tienes una idea concreta. PRs bienvenidos, especialmente para:

- Soporte de más extractores problemáticos
- Mejoras en el sistema de cola
- Tests automatizados

---

## Licencia

MIT — úsalo, modifícalo, compártelo. Un crédito siempre se agradece.

---

<div align="center">

Hecho por [D4vRAM](https://github.com/D4vRAM369)

</div>

---
---

<a name="english"></a>

<div align="center">

# DownloadThis Pro

**GUI for yt-dlp — extract audio from YouTube, SoundCloud and 1000+ sites, without the hassle**

</div>

---

## What is this?

DownloadThis is a graphical interface for [yt-dlp](https://github.com/yt-dlp/yt-dlp) built with Python and tkinter. The idea is simple: you have URLs, you want files on your disk, without touching the terminal every time.

No tracking, no account needed, nothing gets uploaded anywhere. Everything runs locally.

It started as a personal project because existing GUIs were either too basic or too bloated. This one does what I need, with a design that echoes P2P clients from the 2000s — eMule, Ares, DC++ — because that aesthetic has something modern apps have lost: brutal clarity.

---

## Features

- **Download queue** with per-item progress bar, real-time speed and ETA
- **Formats**: mp3, m4a, flac, opus, wav and anything yt-dlp supports
- **Configurable quality** (0–9 for audio)
- **Browser cookie support** (Brave, Firefox, Chrome) for sites requiring login
- **Full playlist download** with a single toggle
- **Drag & drop** for URLs and `.txt` files with link lists
- **Anti-403** mode and **No-DASH** auto-fallback for problematic sites
- **Customizable filename templates** (`%(title)s.%(ext)s`, etc.)
- **Real-time activity log** with timestamps
- **Persistent config** stored at `~/.config/downloadthis/config.json`
- **Status bar** showing global speed, active downloads, and yt-dlp version
- **Queue auto-save** on close — restored on next launch

---

## Requirements

| Tool | Required | Install |
|------|----------|---------|
| **Python 3.9+** | ✅ | [python.org](https://python.org) |
| **yt-dlp** | ✅ | `pip install yt-dlp` |
| **ffmpeg** | ✅ | see below |
| **aria2c** | ❌ optional | faster multi-connection downloads |

```bash
# ffmpeg on Debian/Ubuntu
sudo apt install ffmpeg

# ffmpeg on Arch
sudo pacman -S ffmpeg

# ffmpeg on Windows (winget)
winget install ffmpeg

# aria2c (optional)
sudo apt install aria2
```

---

## Installation

```bash
# Clone the repository
git clone https://github.com/D4vRAM369/downloadthis.git
cd downloadthis

# Install Python dependencies
pip install -r requirements.txt

# Launch the app
python3 downloadthis_modern.py
```

> On first run, the app auto-installs any missing Python dependency.

---

## Quick start

```
1. Copy a URL (Ctrl+C in your browser)
2. In the app → "📋 Pegar URL"  or Ctrl+V
3. Choose destination folder with "📁 Destino"
4. Click "▼ DESCARGAR TODO"
```

For full instructions, cookies, playlists, and troubleshooting → **[USAGE_GUIDE.md](USAGE_GUIDE.md)**

---

## Project structure

```
downloadthis/
├── downloadthis_modern.py     # Full app (~1800 lines)
├── requirements.txt           # pip dependencies
├── pyproject.toml             # Build metadata
├── README.md
├── USAGE_GUIDE.md             # Step-by-step usage guide (public)
└── ~/.config/downloadthis/    # Generated at runtime
    ├── config.json            # Persistent config
    └── logs/
        └── YYYY-MM-DD.txt     # Session logs
```

---

## License

MIT — use it, modify it, share it. A credit is always appreciated.

---

<div align="center">

Built by [D4vRAM](https://github.com/D4vRAM369)

</div>
