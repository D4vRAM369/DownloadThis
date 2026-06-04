# DownloadThis Pro — Guía de Uso / Usage Guide

> GUI para yt-dlp con diseño vintage XP Luna P2P  
> Versión 1.0 · D4vRAM369 · audio-only

---

## Índice / Table of Contents

1. [Instalación](#1-instalación--installation)
2. [Interfaz — Qué es cada parte](#2-interfaz)
3. [Configuración inicial (una sola vez)](#3-configuración-inicial)
4. [Extraer audio de una URL](#4-extraer-audio-de-una-url)
5. [Descargar una Playlist completa](#5-descargar-una-playlist-completa)
6. [Cookies para sitios con login (YouTube, etc.)](#6-cookies-para-sitios-con-login)
7. [Opciones avanzadas](#7-opciones-avanzadas)
8. [Solución de problemas](#8-solución-de-problemas)
9. [Atajos de teclado](#9-atajos-de-teclado)

---

## 1. Instalación / Installation

### Requisitos previos

```bash
# Python 3.9 o superior (verificar)
python3 --version

# ffmpeg — OBLIGATORIO para conversión de audio
# Debian/Ubuntu:
sudo apt install ffmpeg

# Arch:
sudo pacman -S ffmpeg

# Windows (winget):
winget install ffmpeg

# aria2c — OPCIONAL, mejora velocidad en algunos casos
sudo apt install aria2
```

### Instalar la app

```bash
git clone https://github.com/D4vRAM369/downloadthis.git
cd downloadthis

pip install -r requirements.txt

python3 downloadthis_modern.py
```

> La app detecta e instala dependencias Python faltantes en el primer arranque.

---

### Installation (English)

**Prerequisites:**

```bash
# Python 3.9+ required
python3 --version

# ffmpeg — REQUIRED for audio conversion
# Debian/Ubuntu:
sudo apt install ffmpeg

# Arch:
sudo pacman -S ffmpeg

# Windows (winget):
winget install ffmpeg

# aria2c — OPTIONAL, faster downloads in some cases
sudo apt install aria2
```

**Install the app:**

```bash
git clone https://github.com/D4vRAM369/downloadthis.git
cd downloadthis

pip install -r requirements.txt

python3 downloadthis_modern.py
```

---

## 2. Interfaz

```
┌─────────────────────────────────────────────────────────────────────┐
│ ⬇  DownloadThis Pro                          GUI para yt-dlp        │  ← Barra título
├──────────────────────────────────────────────────────────────────────┤
│ 📁 Destino │ 📋 Pegar URL │ + Añadir │ 💾 Guardar │ ▶ Iniciar │ ⏹ │  ← Toolbar
├─ Destino: /home/user/Descargas  ────────────────────────────── [📁] ┤  ← Barra destino
├─ Cola de Descargas ──────────────────────────┬─ Opciones Avanzadas ─┤
│ Nombre             │ Tamaño │Progreso│ Estado │ Formato      [mp3▼] │
│ youtube.com/watch… │  8.4MB │ ████░░ │ ↓1.2MB │ Calidad (0-9) [0 ] │
│ soundcloud.com/…   │   —    │  ———   │En cola │ Cookies Nav [none▼] │
├─ Registro de Actividad ──────────────────────┤ Cookies.txt   [… ] │
│ [20:24:26] [*] yt-dlp → 2025.11.12          │ Plantilla      [▼ ] │
│ [20:24:27] $ yt-dlp -f bestaudio/best …     │ Args extra     [  ] │
│ [20:24:28] [OK] Descarga completada         │ ☐ Playlist completa  │
│                                              │ ⚡ Anti-403 ◈ No-DASH│
│                                              │ ▼ DESCARGAR TODO     │
│                                              │ 💾 Guardar Config    │
├──────────────────────────────────────────────┴──────────────────────┤
│ Cola: 2 elementos  │ Descargando: 1  │ Destino: ~/Descargas  │yt-dlp│  ← Statusbar
└─────────────────────────────────────────────────────────────────────┘
```

| Zona | Para qué sirve |
|------|----------------|
| **Toolbar** | Acciones rápidas — destino, pegar, guardar cola, iniciar/detener |
| **Cola de Descargas** | Lista visual de URLs con progreso en tiempo real |
| **Registro de Actividad** | Log detallado de lo que hace yt-dlp por debajo |
| **Opciones Avanzadas** | Formato, calidad, cookies, plantilla, args extra |
| **Statusbar** | Estado global: elementos en cola, activos, destino actual, versión yt-dlp |

---

## 3. Configuración inicial

Hazlo **una sola vez**. Quedará guardado.

### 3.1 Carpeta de destino

Click en **📁 Destino** en la toolbar → selecciona la carpeta donde quieres los archivos.  
También puedes escribir la ruta directamente en el campo de texto.

### 3.2 Formato y calidad

| Formato | Cuándo usarlo |
|---------|---------------|
| `mp3` | Compatibilidad universal — reproductores, WhatsApp, todo |
| `m4a` | Calidad ligeramente mejor que mp3 al mismo tamaño |
| `flac` | Sin pérdida de calidad — archivos grandes |
| `opus` | Mejor calidad/tamaño — solo reproductores modernos |
| `wav` | Sin compresión — edición profesional |

**Calidad (0–9):** solo afecta a formatos con compresión (mp3, opus, m4a).  
`0` = mejor calidad (archivo más grande). `9` = peor calidad (archivo más pequeño).  
**Recomendado: `0`**

### 3.3 Guardar configuración

Click en **💾 Guardar Configuración** en el panel derecho.  
Se guarda en `~/.config/downloadthis/config.json`.

---

## 4. Extraer audio de una URL

### Flujo básico

```
1. Copia la URL en el navegador  (Ctrl+C)
2. En la app → click "📋 Pegar URL"  (o Ctrl+V)
3. La URL aparece en la cola con estado "En cola"
4. Click "▼ DESCARGAR TODO"
```

### ¿Qué ves en la cola?

| Columna | Significado |
|---------|-------------|
| **Nombre** | Dominio + ruta de la URL |
| **Tamaño** | Tamaño del archivo (aparece durante la descarga) |
| **Progreso** | Barra + porcentaje en tiempo real |
| **Estado** | `En cola` → `↓ velocidad ETA` → `✓ Listo` / `✗ Error` |

### Añadir múltiples URLs

- **Ctrl+V** con varias URLs copiadas — se detectan automáticamente
- **+ Añadir URL** — cuadro de texto multilínea, pega varias a la vez
- **Archivo .txt** — un enlace por línea, arrástralo sobre la cola (drag & drop)
- **Menú Cola → Cargar cola** — carga un `.txt` guardado anteriormente

---

## 5. Descargar una Playlist completa

### Paso a paso

**Paso 1 — Activa el checkbox**

En el panel derecho, marca **"☐ Descargar Playlist completa"** antes de iniciar.

> Activa `--yes-playlist --ignore-errors` en yt-dlp.  
> `--ignore-errors` es clave: si un elemento está eliminado o geo-bloqueado, **lo salta y continúa**.

**Paso 2 — Usa la plantilla de playlist**

Click en **▼** junto al campo Plantilla → selecciona:

```
%(playlist_index)s - %(title)s.%(ext)s
```

Resultado: `001 - Título del audio.mp3`, `002 - ...`, etc.

**Paso 3 — Pega la URL de la playlist**

La URL debe contener `list=`:
```
https://www.youtube.com/watch?v=xxx&list=PLxxxxx...
https://www.youtube.com/playlist?list=PLxxxxx...
```

**Paso 4 — Click "▼ DESCARGAR TODO"**

La cola muestra el progreso global con sub-filas por cada elemento:
```
Cola:  Playlist [47/477]  ← fila principal
       ♪ Título audio 47  ← sub-fila del elemento actual
```

### Playlist ON vs OFF

| Comportamiento | Playlist OFF | Playlist ON |
|----------------|-------------|-------------|
| URL con `?list=` | Extrae audio solo de esa URL | Extrae audio de toda la lista |
| Elemento inaccesible | Falla y para | Lo salta, continúa |
| Plantilla recomendada | `%(title)s.%(ext)s` | `%(playlist_index)s - %(title)s.%(ext)s` |

---

## 6. Cookies para sitios con login

Las cookies son tu sesión de YouTube exportada a un archivo. Le dicen a yt-dlp "soy este usuario logueado" sin necesidad de contraseña. Son necesarias para extraer audio de contenido con login, edad restringida, o cuando YouTube bloquea la descarga.

### Opción A — Archivo Cookies.txt (recomendada)

Más fiable que leer del navegador. No requiere que el navegador esté cerrado.

#### Paso 1 — Instala la extensión correcta

> ⚠️ Hay extensiones falsas con nombres parecidos. Instala **exactamente** estas:

| Navegador | Extensión a instalar | Dónde encontrarla |
|-----------|----------------------|-------------------|
| **Chrome / Brave** | **Get cookies.txt LOCALLY** | Chrome Web Store → busca `cookies.txt LOCALLY` |
| **Firefox** | **cookies.txt** (de Lennon Hill) | Firefox Add-ons → busca `cookies.txt` |

**Chrome/Brave — verificación:** el ícono es una galleta marrón 🍪. Autor: **Rahul Shaw**. ID de extensión: `cclelndahbckbenkjhflpdbgdldlbecc`.

**Firefox — verificación:** aparece como "cookies.txt" con ícono de galleta. Autor: **Lennon Hill**.

#### Paso 2 — Inicia sesión en YouTube

Abre Chrome o Brave → ve a `youtube.com` → inicia sesión con tu cuenta Google.  
Verifica que estés logueado (aparece tu foto/avatar arriba a la derecha).

#### Paso 3 — Exporta las cookies

1. Estando en `youtube.com` (sin navegar a ningún contenido específico)
2. Haz click en el ícono 🍪 de la extensión en la barra de extensiones del navegador
3. Click en **"Export"** o **"Click here to export cookies"**
4. Se descarga automáticamente `cookies.txt` o `youtube.com_cookies.txt`

#### Paso 4 — Guarda el archivo en lugar fijo

Mueve el archivo a una ubicación permanente. Recomendado:

```
Linux:   /home/TU_USUARIO/.config/downloadthis/cookies.txt
Windows: C:\Users\TU_USUARIO\.config\downloadthis\cookies.txt
```

No lo dejes en Descargas donde puedes borrarlo por error.

#### Paso 5 — Selecciónalo en DownloadThis Pro

1. Panel derecho → campo **Cookies.txt** → click en **`…`**
2. Navega hasta el archivo y selecciónalo
3. La ruta aparece en el campo
4. Click **💾 Guardar Configuración**

A partir de ahora cada descarga usará tus cookies automáticamente.

#### Verificación rápida

```bash
yt-dlp --cookies ~/.config/downloadthis/cookies.txt --no-playlist --simulate \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Si ves `Downloading 1 format(s)` → cookies válidas ✅  
Si ves `Sign in to confirm` → cookies expiradas, renuévalas ❌

#### ¿Cuándo renovar las cookies?

| Situación | Acción |
|-----------|--------|
| Más de 2 semanas sin renovarlas | Exporta de nuevo |
| Cerraste sesión en el navegador | Vuelve a loguearte y exporta |
| Cambiaste la contraseña de Google | Exporta de nuevo |
| yt-dlp da `Sign in to confirm` | Renuévalas |

**Proceso de renovación:** repite pasos 2→5, sobreescribe el archivo anterior.

---

### Opción B — Cookies del navegador directamente

| Valor | Cuándo usarlo |
|-------|---------------|
| `chrome` / `brave` / `firefox` | Si no quieres instalar extensión |
| `none` | Videos públicos sin restricción |

> ⚠️ El navegador debe estar **completamente cerrado** al momento de descargar.  
> Si tienes `Cookies.txt` configurado, tiene prioridad y esta opción se ignora.

---

## 7. Opciones avanzadas

### Botones especiales

**⚡ Anti-403** — Úsalo cuando YouTube bloquea la descarga con error `403 Forbidden`.  
Añade headers HTTP que simulan un navegador real y activa cookies de Firefox automáticamente.  
Es idempotente: hacer click dos veces no duplica los parámetros.

**◈ No-DASH** — Úsalo si la extracción falla, sale corrupta o yt-dlp elige un flujo problemático.
Fuerza un formato sin DASH manifest (protocolo alternativo de streaming).

> Estos botones modifican el campo **Args extra**. Para que sean permanentes, click en **💾 Guardar Configuración**.

### Plantillas de nombre

| Plantilla | Ejemplo de resultado |
|-----------|---------------------|
| `%(title)s.%(ext)s` | `Lo-fi Mix 2024.mp3` |
| `%(uploader)s - %(title)s.%(ext)s` | `ChilledCow - Lo-fi Mix 2024.mp3` |
| `%(playlist_index)s - %(title)s.%(ext)s` | `042 - Lo-fi Mix 2024.mp3` |
| `%(upload_date)s - %(title)s.%(ext)s` | `20240115 - Lo-fi Mix 2024.mp3` |

### Args extra útiles

```bash
--embed-subs --sub-lang es          # Incrustar subtítulos en español
--write-thumbnail                   # Guardar carátula como imagen separada
--limit-rate 500K                   # Limitar velocidad a 500 KB/s
--geo-bypass                        # Intentar saltar restricciones geográficas
--playlist-start 10 --playlist-end 50  # Extraer solo del elemento 10 al 50 de una lista
--concurrent-fragments 4            # Descarga paralela (más rápido en conexiones rápidas)
```

### Guardar y cargar cola

- **💾 Guardar cola** → exporta la lista de URLs a un `.txt`
- **📂 Cargar cola** → importa un `.txt` con URLs (una por línea)

La cola también se **auto-guarda al cerrar** la app y se **restaura automáticamente** al volver a abrirla.

---

## 8. Solución de problemas

| Error / Síntoma | Causa probable | Solución |
|-----------------|----------------|----------|
| `403 Forbidden` | YouTube bloquea sin cookies | Activa **⚡ Anti-403** + configura cookies |
| `Sign in to confirm your age` | Contenido con restricción de edad | Configura cookies con sesión iniciada |
| `Requested format is not available` | Elemento privado/eliminado en playlist | Activa **☐ Playlist completa** (incluye `--ignore-errors`) |
| `Only images are available` | Contenido restringido o Short eliminado | Normal en playlists grandes — se salta con playlist ON |
| Audio corrupto o incompleto | Formato DASH sin ffmpeg | `sudo apt install ffmpeg` o activa **◈ No-DASH** |
| Descarga muy lenta | Servidor limita velocidad | Añade en Args extra: `--concurrent-fragments 4` |
| Playlist procesa solo 1 elemento | Checkbox desactivado | Marca **☐ Descargar Playlist completa** |
| App no arranca | yt-dlp o ffmpeg no instalados | `pip install -U yt-dlp` · `sudo apt install ffmpeg` |
| Cookies no funcionan | Expiradas o mal exportadas | Renueva las cookies siguiendo la [sección 6](#6-cookies-para-sitios-con-login) |

### Ver los logs completos

```
~/.config/downloadthis/logs/YYYY-MM-DD.txt
```

Menú **Archivo → Abrir carpeta de logs** para acceder directamente desde la app.

---

## 9. Atajos de teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+V` | Pegar URL desde portapapeles y añadir a la cola |
| `Ctrl+Enter` | Iniciar todas las descargas |
| `Supr` | Eliminar elemento seleccionado de la cola |

---

*USAGE_GUIDE v1.0 — Actualizado 2026-06-04*
