#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
downloadthis_modern — GUI para yt-dlp  |  Diseño vintage P2P (XP Luna)
"""

import os, re, sys, json, queue, shlex, signal, subprocess, threading
from pathlib import Path
import importlib
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
from datetime import datetime

# ============================================================
#  AUTO-INSTALL
# ============================================================

def ensure_python_packages():
    required = {
        "ttkbootstrap": "ttkbootstrap",
        "tkinterdnd2":  "tkinterdnd2",
        "yt_dlp":       "yt-dlp",
    }
    for module_name, pip_name in required.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            try:
                print(f"[SETUP] Instalando '{pip_name}'…")
                subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
                print(f"[SETUP] '{pip_name}' instalado.")
            except Exception as exc:
                print(f"[SETUP] No se pudo instalar '{pip_name}': {exc}")

ensure_python_packages()

# ============================================================
#  OPTIONAL IMPORTS
# ============================================================

# ttkbootstrap importado pero no usado para widgets —
# usamos raw tk.* para control total de colores (XP Luna)
try:
    import ttkbootstrap  # noqa: F401
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    TTKBOOTSTRAP_AVAILABLE = False

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES, DND_TEXT
    DND_AVAILABLE = True
except Exception:
    TkinterDnD = None
    DND_FILES = DND_TEXT = None
    DND_AVAILABLE = False

# ============================================================
#  DESIGN SYSTEM — XP Luna Vintage
# ============================================================
# Colores y fuentes extraídos del mockup HTML.
# Raw tk.* widgets (no ttk) para que bg/fg/relief sean exactos.

BG_MAIN        = "#ece9d8"
BG_PANEL_HDR   = "#d4d0c8"
BG_TOOLBAR     = "#dedad2"
BG_TITLEBAR    = "#082984"
BG_SELECTED    = "#082984"
BG_EVEN_ROW    = "#eef3ff"
BG_LOG         = "#0a0a0a"
FG_LOG         = "#00cc00"
FG_LOG_TS      = "#446644"
FG_LOG_INFO    = "#6699ff"
FG_LOG_WARN    = "#ffaa00"
FG_STATUS_DL   = "#006600"
FG_STATUS_Q    = "#886600"
FG_STATUS_DONE = "#004488"
PROGRESS_GREEN = "#1a8a1a"
BTN_AMBER_BG   = "#e8c840"
BTN_BLUE_BG    = "#80a8e8"

FONT_UI    = ("Tahoma", 9)
FONT_BOLD  = ("Tahoma", 9, "bold")
FONT_LOG   = ("Courier New", 9)
FONT_SMALL = ("Tahoma", 8)

# ============================================================
#  REGEX + PARSERS  (sin cambios)
# ============================================================

STRICT_URL_RE = re.compile(
    r"""(?ix)
    \b(
      (?:https?://|www\.)
      [a-z0-9][a-z0-9.-]+\.[a-z]{2,}
      (?:/[^\s<>"']*)?
    )
    """
)
YTSEARCH_RE       = re.compile(r'(?i)\bytsearch(?::\d+)?\s*:[^\s].+')
PROGRESS_RE       = re.compile(r"^\[download\]\s+(\d{1,3}(?:\.\d+)?)%")
PROGRESS_DETAIL_RE = re.compile(
    r'^\[download\]\s+(\d{1,3}(?:\.\d+)?)%\s+of\s+([^\s]+)\s+at\s+([^\s]+)\s+ETA\s+([^\s]+)'
)
SPEED_RE          = re.compile(r'at\s+([0-9.]+[KMGT]?i?B/s)')
ETA_RE            = re.compile(r'ETA\s+(\d{2}:\d{2}|\d+:\d{2}:\d{2})')
SIZE_RE           = re.compile(r'(\d+(?:\.\d+)?[KMGT]?i?B)')
PLAYLIST_INDEX_RE = re.compile(r'\[download\] Downloading (?:video|item) (\d+) of (\d+)')
EXTRACT_AUDIO_RE  = re.compile(r'\[ExtractAudio\] Destination:\s*(.+)')


class DownloadProgress:
    def __init__(self, percent=None, size=None, speed=None, eta=None,
                 item_current=None, item_total=None):
        self.percent = percent;  self.size  = size
        self.speed   = speed;    self.eta   = eta
        self.item_current = item_current
        self.item_total   = item_total

    def __str__(self):
        parts = []
        if self.percent is not None:              parts.append(f"{self.percent}%")
        if self.speed:                            parts.append(self.speed)
        if self.eta:                              parts.append(f"ETA {self.eta}")
        if self.item_current and self.item_total: parts.append(f"[{self.item_current}/{self.item_total}]")
        return " • ".join(parts) if parts else "Descargando..."


def parse_progress_line(line: str):
    if not line.startswith('[download]'):
        return None
    m = PROGRESS_DETAIL_RE.match(line.strip())
    if m:
        return DownloadProgress(float(m.group(1)), m.group(2), m.group(3), m.group(4))
    percent = speed = eta = None
    m = PROGRESS_RE.match(line.strip())
    if m: percent = float(m.group(1))
    m = SPEED_RE.search(line)
    if m: speed = m.group(1)
    m = ETA_RE.search(line)
    if m: eta = m.group(1)
    if percent is not None or speed or eta:
        return DownloadProgress(percent, None, speed, eta)
    m = PLAYLIST_INDEX_RE.search(line)
    if m:
        return DownloadProgress(item_current=int(m.group(1)), item_total=int(m.group(2)))
    return None


def extract_urls(text: str):
    urls = set()
    for m in STRICT_URL_RE.finditer(text or ""):
        u = m.group(1).strip().rstrip(').,;')
        urls.add(u)
    for line in (text or "").splitlines():
        line = line.strip()
        if YTSEARCH_RE.fullmatch(line):
            urls.add(line)
    return list(urls)


# ============================================================
#  CONFIG  (sin cambios)
# ============================================================

CONFIG_PATH     = Path.home() / ".config" / "downloadthis" / "config.json"
QUEUE_SAVE_PATH = Path.home() / ".config" / "downloadthis" / "queue_autosave.json"

# Prefer yt-dlp in the venv next to THIS script, not the active Python interpreter
_script_venv_ytdlp = Path(__file__).parent / "venv" / "bin" / "yt-dlp"
_interp_ytdlp      = Path(sys.executable).parent / "yt-dlp"
if _script_venv_ytdlp.exists():
    YTDLP_CMD = str(_script_venv_ytdlp)
elif _interp_ytdlp.exists():
    YTDLP_CMD = str(_interp_ytdlp)
else:
    YTDLP_CMD = "yt-dlp"

# Deno path for yt-dlp JS challenge solving (n-parameter)
_deno = Path.home() / ".deno" / "bin" / "deno"
DENO_RUNTIME_ARG = ["--js-runtimes", f"deno:{_deno}"] if _deno.exists() else []


def ensure_config():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg = {
        "download_dir":    str(Path.home() / "Descargas"),
        "audio_quality":   "0",
        "audio_format":    "mp3",
        "cookies_file":    "",
        "extra_args":      "",
        "browser_cookies": "none",
        "output_template": "%(title)s.%(ext)s",
        "playlist":        False,
    }
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def format_download_error(error, context="descarga"):
    msgs = {
        'TimeoutError':              {'message': f'Tiempo de espera agotado durante {context}',
                                      'suggestion': 'Verifica tu conexión a internet'},
        'ConnectionError':           {'message': f'Error de conexión durante {context}',
                                      'suggestion': 'Comprueba tu conexión a internet'},
        'URLError':                  {'message': 'URL no válida o inaccesible',
                                      'suggestion': 'Verifica que la URL esté correcta'},
        'PermissionError':           {'message': 'Sin permisos para escribir en el destino',
                                      'suggestion': 'Elige otra carpeta de destino'},
        'FileNotFoundError':         {'message': 'Herramienta requerida no encontrada',
                                      'suggestion': 'Instala las dependencias faltantes (yt-dlp, ffmpeg)'},
        'OSError':                   {'message': 'Error del sistema operativo',
                                      'suggestion': 'Verifica permisos y espacio en disco'},
        'subprocess.TimeoutExpired': {'message': 'Proceso cancelado por timeout (>30min)',
                                      'suggestion': 'La descarga era muy lenta. Prueba con otra URL'},
    }
    info = msgs.get(type(error).__name__,
                    {'message': f'Error inesperado: {str(error)[:100]}',
                     'suggestion': 'Revisa el log para más detalles'})
    return f"[ERROR] {info['message']}\n[TIP] {info['suggestion']}\n"


# ============================================================
#  DOWNLOADER THREAD  (sin cambios)
# ============================================================

class Downloader(threading.Thread):
    def __init__(self, url, outdir, attempts, log_queue, done_callback):
        super().__init__(daemon=True)
        self.url = url; self.outdir = outdir
        self.attempts = attempts; self.log_queue = log_queue
        self.done_callback = done_callback
        self.proc = None
        self._stop = threading.Event()
        self._success = False
        self._variant_index = 0

    def _run_one(self, cmd_tokens):
        saw_413 = False
        cmd = list(cmd_tokens) + ["-P", self.outdir, self.url]
        self.log_queue.put(f"$ {' '.join(shlex.quote(c) for c in cmd)}\n")
        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, universal_newlines=True
            )
            for raw_line in self.proc.stdout:
                if self._stop.is_set(): break
                line = raw_line.lstrip("\r")
                if "HTTP Error 413" in line or "Request Entity Too Large" in line:
                    saw_413 = True
                progress_info = parse_progress_line(line.strip())
                if progress_info and progress_info.percent is not None:
                    self.log_queue.put(("progress_detailed", self.url, progress_info))
                    try:
                        self.log_queue.put(("progress", self.url,
                                            int(float(progress_info.percent))))
                    except (ValueError, TypeError):
                        pass
                # Detect new playlist item start
                m_item = PLAYLIST_INDEX_RE.search(line.strip())
                if m_item:
                    self.log_queue.put(("playlist_sub_start", self.url,
                                        int(m_item.group(1)), int(m_item.group(2))))
                # Detect audio extraction = song title
                m_audio = EXTRACT_AUDIO_RE.search(line.strip())
                if m_audio:
                    title = Path(m_audio.group(1).strip()).stem
                    self.log_queue.put(("playlist_sub_title", self.url, title))
                self.log_queue.put(line)
            return self.proc.wait(), saw_413
        except Exception as e:
            self.log_queue.put(format_download_error(e, "ejecución de yt-dlp"))
            return 1, saw_413

    def run(self):
        self._success = False
        try:
            total = len(self.attempts)
            for idx, variant in enumerate(self.attempts):
                self._variant_index = idx
                cmd_tokens = variant["cmd"] if isinstance(variant, dict) else variant
                self.log_queue.put(f"[*] Intento {idx+1}/{total}…\n")
                rc, saw_413 = self._run_one(cmd_tokens)
                if rc == 0 and not saw_413:
                    self.log_queue.put(f"[OK] Descarga completada: {self.url}\n")
                    self._success = True
                    break
                else:
                    motivo = "detectado 413" if saw_413 else f"rc={rc}"
                    self.log_queue.put(f"[!] Falló intento {idx+1} ({motivo}). Probando variante…\n")
            else:
                self.log_queue.put(f"[ERROR] Agotadas variantes para: {self.url}\n")
        finally:
            self.done_callback(self, self._success, self._variant_index)

    def stop(self):
        self._stop.set()
        if self.proc and self.proc.poll() is None:
            try: self.proc.terminate()
            except Exception: pass


# ============================================================
#  CANVAS QUEUE WIDGET
# ============================================================
# Reemplaza tk.Listbox. Dibuja filas con barra de progreso inline.
# 4 columnas: Nombre (dinámico) | Tamaño (70px) | Progreso (80px) | Estado (120px)
# Estado combina velocidad + estado — coincide con el screenshot.

class CanvasQueue(tk.Frame):
    ROW_H       = 20
    COL_SIZE    = 70
    COL_PROG    = 80
    COL_ETA     = 120
    SCROLLBAR_W = 17   # espacio reservado en header para alinear con scrollbar

    def __init__(self, master, **kw):
        kw.setdefault("bg",      "#ffffff")
        kw.setdefault("relief",  "sunken")
        kw.setdefault("bd",      2)
        super().__init__(master, **kw)

        # Header fijo (no hace scroll) — separado del canvas de filas
        hdr_row = tk.Frame(self, bg=BG_PANEL_HDR, height=self.ROW_H)
        hdr_row.pack(fill="x")
        hdr_row.pack_propagate(False)
        self._hdr = tk.Canvas(hdr_row, height=self.ROW_H, bg=BG_PANEL_HDR,
                              highlightthickness=0, bd=0)
        self._hdr.pack(side="left", fill="both", expand=True)
        # Espaciador que compensa el ancho del scrollbar → header alineado con filas
        tk.Frame(hdr_row, bg=BG_PANEL_HDR, width=self.SCROLLBAR_W).pack(side="right")

        tk.Frame(self, bg="#b5b0a0", height=1).pack(fill="x")

        # Canvas de filas + scrollbar
        row_frame = tk.Frame(self, bg="#ffffff")
        row_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(row_frame, bg="#ffffff", highlightthickness=0, bd=0)
        self._canvas.pack(side="left", fill="both", expand=True)

        self._vbar = tk.Scrollbar(row_frame, orient="vertical",
                                  command=self._canvas.yview)
        self._vbar.pack(side="right", fill="y")
        self._canvas.configure(yscrollcommand=self._vbar.set)

        self._items  = []
        self._sel_id = None

        self._canvas.bind("<Button-1>",  self._on_click)
        self._canvas.bind("<Configure>", lambda e: self._on_resize())
        self._hdr.bind("<Configure>",    lambda e: self._redraw_header())

        # Rueda del ratón — Linux usa Button-4/5
        self._canvas.bind("<MouseWheel>",
                          lambda e: self._canvas.yview_scroll(
                              -1 * int(e.delta / 120), "units"))
        self._canvas.bind("<Button-4>",
                          lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<Button-5>",
                          lambda e: self._canvas.yview_scroll(1,  "units"))

    # ── API pública ──────────────────────────────────────────

    def add_item(self, item: dict):
        self._items.append(dict(item))
        self._update_scrollregion()
        self._redraw()

    def update_item(self, item_id: str, **kwargs):
        for it in self._items:
            if it["id"] == item_id:
                it.update(kwargs)
                break
        self._redraw()

    def remove_item(self, item_id: str):
        self._items = [it for it in self._items if it["id"] != item_id]
        if self._sel_id == item_id:
            self._sel_id = None
        self._update_scrollregion()
        self._redraw()

    def clear(self):
        self._items.clear()
        self._sel_id = None
        self._update_scrollregion()
        self._redraw()

    def get_selected_id(self) -> str:
        return self._sel_id

    def count(self) -> int:
        return len(self._items)

    # Delegación DnD
    def register_dnd(self, *types):
        self._canvas.drop_target_register(*types)

    def dnd_bind(self, sequence, func, add=None):
        self._canvas.dnd_bind(sequence, func, add)

    # ── Geometría ────────────────────────────────────────────

    def _name_col_w(self) -> int:
        w = self._canvas.winfo_width()
        if w <= 1:
            return 200
        return max(80, w - self.COL_SIZE - self.COL_PROG - self.COL_ETA)

    def _col_x(self) -> dict:
        n = self._name_col_w()
        return dict(
            name=0,
            size=n,
            prog=n + self.COL_SIZE,
            eta=n  + self.COL_SIZE + self.COL_PROG,
            end=n  + self.COL_SIZE + self.COL_PROG + self.COL_ETA,
        )

    def _update_scrollregion(self):
        h = max(len(self._items) * self.ROW_H, 1)
        self._canvas.configure(
            scrollregion=(0, 0, self._canvas.winfo_width(), h))

    def _on_resize(self):
        self._update_scrollregion()
        self._redraw_header()
        self._redraw()

    # ── Eventos ──────────────────────────────────────────────

    def _on_click(self, event):
        y   = self._canvas.canvasy(event.y)
        idx = int(y // self.ROW_H)
        self._sel_id = (self._items[idx]["id"]
                        if 0 <= idx < len(self._items) else None)
        self._redraw()

    # ── Dibujo ───────────────────────────────────────────────

    def _redraw_header(self):
        self._hdr.delete("all")
        w = self._hdr.winfo_width()
        if w <= 1:
            return
        # Cálculo idéntico al canvas (SCROLLBAR_W ya está compensado por el espaciador)
        n  = max(80, w - self.COL_SIZE - self.COL_PROG - self.COL_ETA)
        cx = dict(name=0, size=n,
                  prog=n + self.COL_SIZE,
                  eta=n  + self.COL_SIZE + self.COL_PROG,
                  end=w)
        self._hdr.create_rectangle(0, 0, w, self.ROW_H, fill=BG_PANEL_HDR, outline="")
        for label, x1, x2 in [
            ("Nombre",   cx["name"], cx["size"]),
            ("Tamaño",   cx["size"], cx["prog"]),
            ("Progreso", cx["prog"], cx["eta"]),
            ("Estado",   cx["eta"],  cx["end"]),
        ]:
            self._hdr.create_text(x1 + 5, self.ROW_H // 2, anchor="w",
                                  text=label, fill="#000000", font=FONT_BOLD)
            if x2 < cx["end"]:
                self._hdr.create_line(x2, 2, x2, self.ROW_H - 2, fill="#b5b0a0")

    def _redraw(self):
        self._canvas.delete("all")
        w = self._canvas.winfo_width()
        if w <= 1:
            self.after(50, self._redraw)
            return
        cx = self._col_x()

        for idx, item in enumerate(self._items):
            y   = idx * self.ROW_H
            sel = (item["id"] == self._sel_id)

            # Fondo de fila: seleccionada=azul, par=blanco, impar=azul claro
            row_bg = BG_SELECTED if sel else ("#ffffff" if idx % 2 == 0 else BG_EVEN_ROW)
            row_fg = "#ffffff"   if sel else "#000000"

            self._canvas.create_rectangle(0, y, w, y + self.ROW_H,
                                          fill=row_bg, outline="")
            self._canvas.create_line(0, y + self.ROW_H - 1, w, y + self.ROW_H - 1,
                                     fill="#2040a0" if sel else "#e8e8e8")

            # Separadores verticales de columna
            for sx in [cx["size"], cx["prog"], cx["eta"]]:
                self._canvas.create_line(sx, y, sx, y + self.ROW_H,
                                         fill="#3050b0" if sel else "#e0e0e0")

            # ── Columna Nombre ──
            name = item.get("name", item["id"])
            max_chars = max(8, (cx["size"] - 12) // 7)  # ~7px/char Tahoma 9
            if len(name) > max_chars:
                name = name[:max_chars - 1] + "…"
            self._canvas.create_text(cx["name"] + 5, y + self.ROW_H // 2,
                                     anchor="w", text=name,
                                     fill=row_fg, font=FONT_UI)

            # ── Columna Tamaño ──
            size_txt = item.get("size") or "—"
            self._canvas.create_text(
                cx["size"] + self.COL_SIZE // 2, y + self.ROW_H // 2,
                anchor="center", text=size_txt,
                fill=row_fg, font=FONT_SMALL)

            # ── Columna Progreso — barra dibujada como rectángulos ──
            pct    = float(item.get("progress") or 0)
            status = item.get("status", "pending")
            bx1 = cx["prog"] + 3;  by1 = y + 4
            bx2 = cx["prog"] + self.COL_PROG - 3;  by2 = y + self.ROW_H - 4
            bw  = bx2 - bx1

            # Fondo barra
            self._canvas.create_rectangle(bx1, by1, bx2, by2,
                                          fill="#cccccc", outline="#888888")
            # Relleno barra
            fill_ratio = min(pct / 100.0, 1.0)
            if fill_ratio > 0:
                self._canvas.create_rectangle(
                    bx1, by1, bx1 + int(bw * fill_ratio), by2,
                    fill=PROGRESS_GREEN, outline="")

            # Texto porcentaje sobre barra
            if   status == "ok":      pct_lbl = "100%"
            elif status == "error":   pct_lbl = "ERR"
            elif status == "pending": pct_lbl = "—"
            else: pct_lbl = f"{int(pct)}%" if pct > 0 else "—"

            pct_fg = "#ffffff" if fill_ratio > 0.55 else "#333333"
            self._canvas.create_text(
                cx["prog"] + self.COL_PROG // 2, y + self.ROW_H // 2,
                anchor="center", text=pct_lbl,
                fill=pct_fg, font=("Tahoma", 7))

            # ── Columna Estado (velocidad + estado) ──
            speed = item.get("speed") or "—"
            eta   = item.get("eta")   or "—"

            if status == "downloading":
                if speed != "—":
                    eta_txt = f"↓ {speed}"
                    if eta != "—": eta_txt += f"  ETA {eta}"
                else:
                    eta_txt = "↓ Descargando"
                eta_fg = "#88ffaa" if sel else FG_STATUS_DL
            elif status == "pending":
                eta_txt = "En cola"
                eta_fg  = "#ffdd88" if sel else FG_STATUS_Q
            elif status == "ok":
                eta_txt = "✓ Listo"
                eta_fg  = "#aaddff" if sel else FG_STATUS_DONE
            elif status == "error":
                eta_txt = "✗ Error"
                eta_fg  = "#ff8888" if sel else "#cc0000"
            else:
                eta_txt = "—"
                eta_fg  = "#cccccc" if sel else "#aaaaaa"

            self._canvas.create_text(
                cx["eta"] + 5, y + self.ROW_H // 2,
                anchor="w", text=eta_txt,
                fill=eta_fg, font=FONT_SMALL)


# ============================================================
#  BASE TK
# ============================================================

if DND_AVAILABLE:
    BaseTk = TkinterDnD.Tk
else:
    BaseTk = tk.Tk


# ============================================================
#  APP
# ============================================================

class App(BaseTk):
    ARG_FLAGS_WITH_VALUE = {
        "-f", "--http-chunk-size", "--extractor-args",
        "--user-agent", "--external-downloader", "--external-downloader-args",
    }
    AVOID_DASH_TOKENS = [
        "-f", "bestaudio[protocol!=http_dash_segments]/bestaudio",
        "--http-chunk-size", "10M", "--hls-prefer-ffmpeg",
    ]

    def __init__(self):
        super().__init__()
        self.title("DownloadThis Pro — GUI para yt-dlp")
        self.geometry("980x720")
        self.minsize(860, 600)
        self.configure(bg=BG_MAIN)

        self.cfg              = ensure_config()
        self.clipboard_last   = ""
        self.urls             = []
        self.item_status      = {}
        self.progress         = {}
        self.progress_details = {}
        self._playlist_current_sub: dict = {}  # parent_url → current sub_item_id
        self._playlist_sub_count:   dict = {}  # parent_url → total items
        self.download_queue   = queue.Queue()
        self.log_queue        = queue.Queue()
        self.active_dl        = None
        self.dl_threads       = set()
        self.ytdlp_available  = True
        self.ffmpeg_available = True
        self.aria2_available  = True
        self.log_file_path    = None
        self._dl_stop_requested = False

        # StringVars de statusbar — creadas antes de _build_ui
        self.sb_queue_var  = tk.StringVar(value="Cola: 0 elementos")
        self.sb_active_var = tk.StringVar(value="Descargando: 0")
        self.sb_dest_var   = tk.StringVar(
            value=f"Destino: {self.cfg.get('download_dir', str(Path.home() / 'Descargas'))}")
        self.sb_ytdlp_var  = tk.StringVar(value="yt-dlp —")

        self._build_ui()
        self._setup_dnd_if_available()
        self.after(800, self._poll_clipboard)
        self.after(80,  self._drain_log_queue)
        self._check_dependencies()
        self._bind_shortcuts()
        self.after(500, self._auto_load_queue)

        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                self._add_urls_from_text(arg)

    # ── UI BUILDERS ─────────────────────────────────────────

    def _build_ui(self):
        # Statusbar primero (side=bottom) para que quede anclado abajo
        self._build_statusbar()
        # Luego de arriba a abajo
        self._build_header_bar()
        self._build_menubar()   # usa configure(menu=) — sin pack
        self._build_toolbar()
        self._build_urlbar()
        self._build_main_area()

    def _build_header_bar(self):
        # Franja azul — evoca titlebar XP sin tocar el chrome del SO
        hdr = tk.Frame(self, bg=BG_TITLEBAR, height=24)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=" ⬇  DownloadThis Pro",
                 bg=BG_TITLEBAR, fg="#ffffff",
                 font=("Tahoma", 10, "bold")).pack(side="left", padx=6)
        tk.Label(hdr, text="GUI para yt-dlp",
                 bg=BG_TITLEBAR, fg="#b8d4f8",
                 font=FONT_UI).pack(side="left")

    def _build_menubar(self):
        # tk.Menu nativo — configure(menu=) lo coloca encima del contenido
        menubar = tk.Menu(self, bg=BG_MAIN, fg="#000000",
                          activebackground=BG_SELECTED, activeforeground="#ffffff",
                          relief="flat", font=FONT_UI)
        self.configure(menu=menubar)

        def cascade(label, entries):
            m = tk.Menu(menubar, tearoff=False, bg=BG_MAIN, fg="#000000",
                        activebackground=BG_SELECTED, activeforeground="#ffffff",
                        font=FONT_UI)
            for e in entries:
                if e is None: m.add_separator()
                else:         m.add_command(label=e[0], command=e[1])
            menubar.add_cascade(label=label, menu=m)

        cascade("Archivo", [
            ("Guardar cola…",          self._save_queue),
            ("Cargar cola…",           self._load_queue),
            None,
            ("Abrir carpeta de logs",  self._open_logs_dir),
            None,
            ("Salir",                  self.destroy),
        ])
        cascade("Cola", [
            ("Pegar desde portapapeles  Ctrl+V", self._paste_from_clipboard),
            ("Añadir URL…",                      self._add_single_url_dialog),
            None,
            ("Eliminar seleccionado  Del",       self._remove_selected),
            ("Limpiar toda la cola",             self._clear_list),
        ])
        cascade("Opciones", [
            ("Guardar configuración",  self._save_options),
            ("Seleccionar destino…",   self._choose_dir),
        ])
        cascade("Herramientas", [
            ("⚡ Preset Anti-403", self._apply_preset),
            ("◈ Aplicar No-DASH",  self._apply_avoid_dash),
        ])
        cascade("Ayuda", [
            ("Ver logs de sesión", self._open_logs_dir),
            ("Acerca de…", lambda: messagebox.showinfo(
                "Acerca de",
                "DownloadThis Pro\nGUI para yt-dlp\n\nRequiere yt-dlp y ffmpeg.")),
        ])

    def _build_toolbar(self):
        # Botones tk.Button con relief=RAISED — look XP exacto
        tk.Frame(self, bg="#ffffff",  height=1).pack(fill="x")  # línea brillo superior

        tb = tk.Frame(self, bg=BG_TOOLBAR)
        tb.pack(fill="x")

        tk.Frame(self, bg="#b5b0a0", height=1).pack(fill="x")   # borde inferior

        def btn(text, cmd, fg="#000000"):
            b = tk.Button(tb, text=text, fg=fg,
                          bg=BG_TOOLBAR, activebackground="#f5f3ee",
                          relief="raised", bd=2, padx=7, pady=2,
                          font=FONT_UI, cursor="hand2", command=cmd)
            b.pack(side="left", padx=2, pady=3)
            return b

        def sep():
            tk.Frame(tb, bg="#b5b0a0", width=1).pack(
                side="left", fill="y", pady=4, padx=2)

        btn("📁 Destino",      self._choose_dir)
        sep()
        btn("📋 Pegar URL",    self._paste_from_clipboard)
        btn("+ Añadir URL",    self._add_single_url_dialog)
        sep()
        btn("💾 Guardar cola", self._save_queue)
        btn("📂 Cargar cola",  self._load_queue)
        sep()
        self.start_btn_tb = btn("▶ Iniciar",  self._start_downloads)
        btn("⏹ Detener",      self._stop_all)
        sep()
        btn("🗑 Limpiar",      self._clear_list, fg="#aa0000")

    def _build_urlbar(self):
        bar = tk.Frame(self, bg=BG_MAIN)
        bar.pack(fill="x", padx=6, pady=3)

        tk.Label(bar, text="Destino:", bg=BG_MAIN, font=FONT_BOLD,
                 width=8, anchor="w").pack(side="left")

        self.dest_var = tk.StringVar(value=self.cfg.get(
            "download_dir", str(Path.home() / "Descargas")))
        ent = tk.Entry(bar, textvariable=self.dest_var,
                       bg="#ffffff", relief="sunken", bd=2,
                       font=FONT_UI, highlightthickness=0)
        ent.pack(side="left", fill="x", expand=True, ipady=2)

        tk.Button(bar, text="📁", width=3,
                  bg=BG_TOOLBAR, activebackground="#f5f3ee",
                  relief="raised", bd=2, font=FONT_UI, cursor="hand2",
                  command=self._choose_dir).pack(side="left", padx=(4, 0), ipady=1)

        tk.Frame(self, bg="#b5b0a0", height=1).pack(fill="x")

    def _build_main_area(self):
        # PanedWindow horizontal: izquierda crece, derecha fija ~215px
        paned = tk.PanedWindow(self, orient="horizontal",
                               bg=BG_MAIN, sashwidth=5,
                               sashrelief="raised", relief="flat", bd=0)
        paned.pack(fill="both", expand=True)

        left  = tk.Frame(paned, bg=BG_MAIN)
        right = tk.Frame(paned, bg=BG_MAIN)
        paned.add(left,  minsize=300, stretch="always")
        paned.add(right, minsize=200, stretch="never")
        paned.paneconfig(right, width=215)

        self._build_left_panel(left)
        self._build_right_panel(right)

    def _build_left_panel(self, parent):
        # ── Cabecera cola ──
        q_hdr = tk.Frame(parent, bg=BG_PANEL_HDR)
        q_hdr.pack(fill="x")
        tk.Label(q_hdr, text="🔥 Cola de Descargas",
                 bg=BG_PANEL_HDR, font=FONT_BOLD, anchor="w").pack(side="left", padx=6, pady=3)
        self.queue_hdr_count = tk.StringVar(value="0 elementos")
        tk.Label(q_hdr, textvariable=self.queue_hdr_count,
                 bg=BG_PANEL_HDR, fg="#666666",
                 font=FONT_SMALL).pack(side="right", padx=8)
        tk.Frame(parent, bg="#b5b0a0", height=1).pack(fill="x")

        # ── CanvasQueue — ocupa todo el espacio vertical disponible ──
        self.canvas_queue = CanvasQueue(parent)
        self.canvas_queue.pack(fill="both", expand=True, padx=4, pady=(4, 0))

        # ── Hint DnD ──
        self.dnd_label = tk.Label(
            parent,
            text="— arrastra enlaces o archivos .txt aquí —",
            bg=BG_MAIN, fg="#aaaaaa", font=("Tahoma", 8))
        self.dnd_label.pack(pady=(2, 2))
        tk.Frame(parent, bg="#b5b0a0", height=1).pack(fill="x")

        # ── Cabecera log ──
        log_hdr = tk.Frame(parent, bg=BG_PANEL_HDR)
        log_hdr.pack(fill="x")
        tk.Label(log_hdr, text="🔥 Registro de Actividad",
                 bg=BG_PANEL_HDR, font=FONT_BOLD, anchor="w").pack(side="left", padx=6, pady=3)
        tk.Frame(parent, bg="#b5b0a0", height=1).pack(fill="x")

        # ── Log: fondo negro, texto verde — terminal vintage ──
        log_outer = tk.Frame(parent, bg=BG_LOG)
        log_outer.pack(fill="both", padx=4, pady=(3, 4))

        self.log = tk.Text(log_outer, bg=BG_LOG, fg=FG_LOG,
                           font=FONT_LOG, height=7, wrap="word",
                           bd=0, highlightthickness=0,
                           insertbackground=FG_LOG,
                           selectbackground=BG_SELECTED)
        self.log.pack(side="left", fill="both", expand=True)

        log_sb = tk.Scrollbar(log_outer, orient="vertical", command=self.log.yview)
        log_sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=log_sb.set)

        self.log.tag_config("ts",      foreground=FG_LOG_TS)
        self.log.tag_config("default", foreground=FG_LOG)
        self.log.tag_config("error",   foreground=FG_LOG_WARN)
        self.log.tag_config("ok",      foreground=FG_LOG)
        self.log.tag_config("info",    foreground=FG_LOG_INFO)
        self.log.tag_config("cmd",     foreground="#555555")

    def _build_right_panel(self, parent):
        # ── Cabecera opciones ──
        opt_hdr = tk.Frame(parent, bg=BG_PANEL_HDR)
        opt_hdr.pack(fill="x")
        tk.Label(opt_hdr, text="⚙ Opciones Avanzadas",
                 bg=BG_PANEL_HDR, font=FONT_BOLD, anchor="w").pack(side="left", padx=6, pady=3)
        tk.Frame(parent, bg="#b5b0a0", height=1).pack(fill="x")

        # ── Formulario: ttk.Combobox para dropdowns (look nativo más limpio),
        #    tk.Entry / tk.Checkbutton para el resto (control de color total) ──
        form = tk.Frame(parent, bg=BG_MAIN, padx=8, pady=5)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self.quality_var      = tk.StringVar(value=self.cfg.get("audio_quality", "0"))
        self.format_var       = tk.StringVar(value=self.cfg.get("audio_format",  "mp3"))
        self.browser_var      = tk.StringVar(value=self.cfg.get("browser_cookies", "none"))
        self.template_var     = tk.StringVar(value=self.cfg.get("output_template", "%(title)s.%(ext)s"))
        self.playlist_var     = tk.BooleanVar(value=self.cfg.get("playlist", False))
        self.extra_args_var   = tk.StringVar(value=self.cfg.get("extra_args", ""))
        self.cookies_file_var = tk.StringVar(value=self.cfg.get("cookies_file", ""))

        ENTRY_KW = dict(bg="#ffffff", relief="sunken", bd=2,
                        font=FONT_UI, highlightthickness=0)
        PAD = dict(padx=3, pady=3)

        r = 0

        def lbl(text):
            nonlocal r
            tk.Label(form, text=text, bg=BG_MAIN, font=FONT_UI,
                     anchor="w").grid(row=r, column=0, sticky="w", **PAD)

        # Formato
        lbl("Formato:")
        ttk.Combobox(form, textvariable=self.format_var,
                     values=["mp3", "m4a", "flac", "opus", "wav"],
                     state="readonly", width=10, font=FONT_UI
                     ).grid(row=r, column=1, sticky="ew", **PAD)
        r += 1

        # Calidad
        lbl("Calidad (0-9):")
        tk.Entry(form, textvariable=self.quality_var, width=4, **ENTRY_KW
                 ).grid(row=r, column=1, sticky="w", **PAD)
        r += 1

        # Cookies Nav
        lbl("Cookies Nav:")
        ttk.Combobox(form, textvariable=self.browser_var,
                     values=["none", "brave", "firefox", "chrome"],
                     state="readonly", width=10, font=FONT_UI
                     ).grid(row=r, column=1, sticky="ew", **PAD)
        r += 1

        # Cookies.txt
        lbl("Cookies.txt:")
        cf = tk.Frame(form, bg=BG_MAIN)
        cf.grid(row=r, column=1, sticky="ew", **PAD)
        cf.columnconfigure(0, weight=1)
        self.cookies_entry = tk.Entry(cf, textvariable=self.cookies_file_var, **ENTRY_KW)
        self.cookies_entry.grid(row=0, column=0, sticky="ew")
        tk.Button(cf, text="…", width=2, relief="raised", bd=2,
                  bg=BG_TOOLBAR, activebackground="#f5f3ee",
                  font=FONT_UI, command=self._choose_cookies_file
                  ).grid(row=0, column=1, padx=(2, 0))
        r += 1

        # Plantilla
        lbl("Plantilla:")
        tpl_f = tk.Frame(form, bg=BG_MAIN)
        tpl_f.grid(row=r, column=1, sticky="ew", **PAD)
        tpl_f.columnconfigure(0, weight=1)
        self.template_entry = tk.Entry(tpl_f, textvariable=self.template_var, **ENTRY_KW)
        self.template_entry.grid(row=0, column=0, sticky="ew")
        self.template_presets = [
            ("%(title)s.%(ext)s",
             "%(title)s.%(ext)s"),
            ("%(playlist_index)s - %(title)s.%(ext)s",
             "%(playlist_index)s - %(title)s.%(ext)s"),
            ("%(uploader)s - %(title)s.%(ext)s",
             "%(uploader)s - %(title)s.%(ext)s"),
        ]
        self.template_menu = tk.Menu(
            self, tearoff=False, bg="#ffffff", font=FONT_UI,
            activebackground=BG_SELECTED, activeforeground="#ffffff")
        for label, tpl in self.template_presets:
            self.template_menu.add_command(label=label,
                                           command=lambda t=tpl: self._set_template(t))
        self.template_btn = tk.Button(tpl_f, text="▼", width=2,
                                      relief="raised", bd=2, bg=BG_TOOLBAR,
                                      activebackground="#f5f3ee", font=FONT_UI,
                                      command=self._open_template_menu)
        self.template_btn.grid(row=0, column=1, padx=(2, 0))
        r += 1

        # Args extra
        lbl("Args extra:")
        tk.Entry(form, textvariable=self.extra_args_var, **ENTRY_KW
                 ).grid(row=r, column=1, sticky="ew", **PAD)
        r += 1

        # Separador
        tk.Frame(form, bg="#b5b0a0", height=1).grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=5)
        r += 1

        # Checkbox playlist
        tk.Checkbutton(form, text="Descargar Playlist completa",
                       variable=self.playlist_var,
                       bg=BG_MAIN, fg="#000000", font=FONT_UI,
                       activebackground=BG_MAIN, selectcolor="#ffffff",
                       relief="flat", cursor="hand2"
                       ).grid(row=r, column=0, columnspan=2, sticky="w", pady=2)
        r += 1

        # ── Botones especiales Anti-403 / No-DASH ──
        tk.Frame(parent, bg="#b5b0a0", height=1).pack(fill="x", pady=(4, 0))
        spec = tk.Frame(parent, bg=BG_MAIN)
        spec.pack(fill="x", padx=6, pady=5)

        tk.Button(spec, text="⚡ Anti-403",
                  bg=BTN_AMBER_BG, activebackground="#d4b420",
                  relief="raised", bd=2, font=FONT_BOLD,
                  fg="#664400", cursor="hand2",
                  command=self._apply_preset
                  ).pack(side="left", fill="x", expand=True, padx=(0, 3), ipady=3)

        tk.Button(spec, text="◈ No-DASH",
                  bg=BTN_BLUE_BG, activebackground="#6090d0",
                  relief="raised", bd=2, font=FONT_BOLD,
                  fg="#002288", cursor="hand2",
                  command=self._apply_avoid_dash
                  ).pack(side="left", fill="x", expand=True, ipady=3)

        # ── Botón principal DESCARGAR TODO ──
        tk.Frame(parent, bg="#b5b0a0", height=1).pack(fill="x")
        self.start_btn = tk.Button(
            parent, text="▼  DESCARGAR TODO",
            bg="#228822", activebackground="#1a6618",
            fg="#ffffff", activeforeground="#ffffff",
            relief="raised", bd=3, font=("Tahoma", 11, "bold"),
            cursor="hand2", command=self._start_downloads)
        self.start_btn.pack(fill="x", padx=6, pady=6, ipady=6)

        # ── Guardar configuración ──
        tk.Button(parent, text="💾 Guardar Configuración",
                  bg=BG_TOOLBAR, activebackground="#f5f3ee",
                  relief="raised", bd=2, font=FONT_UI, cursor="hand2",
                  command=self._save_options
                  ).pack(fill="x", padx=6, pady=(0, 6), ipady=2)

    def _build_statusbar(self):
        # 4 paneles inset en la barra de estado — XP clásico
        sb = tk.Frame(self, bg=BG_TOOLBAR)
        sb.pack(fill="x", side="bottom")
        tk.Frame(self, bg="#ffffff", height=1).pack(fill="x", side="bottom")

        SB = dict(relief="sunken", bd=2, bg=BG_MAIN,
                  font=FONT_SMALL, anchor="w", padx=5, pady=1)
        tk.Label(sb, textvariable=self.sb_queue_var,  **SB).pack(
            side="left",  fill="x", expand=True, padx=2, pady=2)
        tk.Label(sb, textvariable=self.sb_active_var, **SB).pack(
            side="left",  fill="x", expand=True, padx=2, pady=2)
        tk.Label(sb, textvariable=self.sb_dest_var,   **SB).pack(
            side="left",  fill="x", expand=True, padx=2, pady=2)
        tk.Label(sb, textvariable=self.sb_ytdlp_var,  **SB).pack(
            side="right", fill="x",              padx=2, pady=2)

    # ── DnD ─────────────────────────────────────────────────

    def _setup_dnd_if_available(self):
        if not DND_AVAILABLE:
            return
        try:
            self.canvas_queue.register_dnd(DND_FILES, DND_TEXT)
            self.canvas_queue.dnd_bind("<<Drop>>", self._on_drop)
            self.dnd_label.configure(
                text="⬇ Arrastra enlaces, URLs o archivos .txt aquí")
        except Exception as exc:
            self._log_line(f"[AVISO] No se pudo activar drag&drop: {exc}\n", "error")

    def _on_drop(self, event):
        data  = getattr(event, "data", "") or ""
        parts = [p.strip() for p in re.split(r"[\r\n]+", data) if p.strip()]
        if not parts:
            return
        total = 0; has_file = False
        for raw in parts:
            if raw.startswith("{") and raw.endswith("}"): raw = raw[1:-1]
            p = raw.strip().strip('"').strip("'")
            if not p: continue
            if os.path.exists(p):
                has_file = True
                if os.path.isdir(p): continue
                if p.lower().endswith(".txt"):
                    try:
                        content = Path(p).read_text(encoding="utf-8", errors="ignore")
                        total += self._add_urls(extract_urls(content))
                    except Exception as exc:
                        self._log_line(f"[ERROR] No pude leer {p}: {exc}\n", "error")
                else:
                    total += self._add_urls(extract_urls(p))
            else:
                total += self._add_urls(extract_urls(p))
        if total:
            suffix = " de archivo(s)" if has_file else ""
            self._log_line(f"[+DnD] Añadidas {total} URL(s){suffix}.\n", "info")

    # ── PORTAPAPELES ─────────────────────────────────────────

    def _poll_clipboard(self):
        try:
            data = self.clipboard_get()
        except tk.TclError:
            data = ""
        if data != self.clipboard_last:
            self.clipboard_last = data
            if extract_urls(data):
                self._update_statusbars()
        self.after(800, self._poll_clipboard)

    def _update_statusbars(self):
        n     = len(self.urls)
        n_act = sum(1 for u in self.urls
                    if self.item_status.get(u) == "downloading")
        self.sb_queue_var.set(f"Cola: {n} elemento{'s' if n != 1 else ''}")
        self.sb_active_var.set(f"Descargando: {n_act}")
        self.queue_hdr_count.set(f"{n} elemento{'s' if n != 1 else ''}")

    # ── ATAJOS ───────────────────────────────────────────────

    def _bind_shortcuts(self):
        self.bind("<Control-v>",      lambda _e: self._paste_from_clipboard())
        self.bind("<Delete>",         lambda _e: self._remove_selected())
        self.bind("<Control-Return>", lambda _e: self._start_downloads())

    def _paste_from_clipboard(self):
        try:
            data = self.clipboard_get()
        except tk.TclError:
            data = ""
        if not data:
            messagebox.showinfo("Portapapeles", "No hay texto en el portapapeles.")
            return
        self._add_urls_from_text(data)

    def _add_single_url_dialog(self):
        win = tk.Toplevel(self)
        win.title("Añadir URL")
        win.resizable(False, False)
        win.configure(bg=BG_MAIN)
        tk.Label(win, text="Pega una URL o varias (una por línea):",
                 bg=BG_MAIN, font=FONT_UI).pack(anchor="w", padx=10, pady=(10, 4))
        txt = tk.Text(win, width=70, height=8, bg="#ffffff", fg="#000000",
                      font=FONT_UI, relief="sunken", bd=2)
        txt.pack(padx=10)
        txt.focus_set()
        tk.Button(win, text="Añadir",
                  bg="#228822", fg="#ffffff",
                  activebackground="#1a6618", activeforeground="#ffffff",
                  relief="raised", bd=2, font=FONT_BOLD, cursor="hand2",
                  command=lambda: (
                      self._add_urls_from_text(txt.get("1.0", "end").strip()),
                      win.destroy())
                  ).pack(pady=10, ipadx=10)
        win.grab_set()
        self.wait_window(win)

    def _add_urls_from_text(self, text):
        urls = extract_urls(text or "")
        if not urls:
            messagebox.showwarning("Sin URLs", "No se detectaron URLs válidas.")
            return
        added = self._add_urls(urls)
        if added:
            self._log_line(f"[+] Añadidas {added} URL(s).\n", "info")

    # ── GESTIÓN DE COLA ──────────────────────────────────────

    @staticmethod
    def _short_name(url: str, max_len: int = 55) -> str:
        m = re.match(r'https?://([^/]+)(/.*)?', url)
        if m:
            domain = m.group(1)
            path   = (m.group(2) or "").rstrip("/")
            tail   = path.split("/")[-1] if path else ""
            name   = f"{domain}/{tail}" if tail else domain
        else:
            name = url
        return name[:max_len - 1] + "…" if len(name) > max_len else name

    def _add_urls(self, urls):
        count = 0
        for u in urls:
            u = u.strip()
            if not u or u in self.urls:
                continue
            self.urls.append(u)
            self.item_status[u] = "pending"
            self.progress[u]    = None
            # CanvasQueue reemplaza tk.Listbox: dibuja filas con barra de progreso
            self.canvas_queue.add_item({
                "id":       u,
                "name":     self._short_name(u),
                "size":     "—",
                "progress": 0.0,
                "speed":    "—",
                "eta":      "—",
                "status":   "pending",
            })
            count += 1
        self._update_statusbars()
        return count

    def _refresh_item_display(self, url):
        if url not in self.urls:
            return
        state  = self.item_status.get(url, "pending")
        pct    = float(self.progress.get(url) or 0)
        speed  = eta = size = "—"
        detail = self.progress_details.get(url)
        if detail:
            if detail.speed: speed = detail.speed
            if detail.eta:   eta   = detail.eta
            if detail.size:  size  = detail.size
        self.canvas_queue.update_item(
            url, status=state, progress=pct, speed=speed, eta=eta, size=size)

    def _set_item_status(self, url, state):
        if url not in self.urls:
            return
        self.item_status[url] = state
        if   state == "downloading":
            if self.progress.get(url) is None: self.progress[url] = 0
        elif state == "pending":
            self.progress[url] = None
        elif state in {"ok", "error"}:
            self.progress.pop(url, None)
        self._refresh_item_display(url)
        self._update_statusbars()

    def _remove_selected(self):
        sel_id = self.canvas_queue.get_selected_id()
        if not sel_id or sel_id not in self.urls:
            return
        self.urls.remove(sel_id)
        self.canvas_queue.remove_item(sel_id)
        self.item_status.pop(sel_id, None)
        self.progress.pop(sel_id, None)
        self.progress_details.pop(sel_id, None)
        self._log_line("[-] Eliminada 1 URL.\n", "info")
        self._update_statusbars()

    def _clear_list(self):
        self.canvas_queue.clear()
        self.urls.clear()
        self.item_status.clear()
        self.progress.clear()
        self.progress_details.clear()
        self._log_line("[*] Cola vaciada.\n", "info")
        self._update_statusbars()

    def _save_queue(self):
        if not self.urls:
            messagebox.showinfo("Cola vacía", "No hay URLs para guardar.")
            return
        initial_dir = self.dest_var.get().strip() or os.path.expanduser("~")
        path = filedialog.asksaveasfilename(
            title="Guardar cola", initialdir=initial_dir,
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Todos los archivos", "*.*")],
            initialfile="downloadthis-queue.txt",
        )
        if not path: return
        try:
            Path(path).write_text("\n".join(self.urls) + "\n", encoding="utf-8")
            self._log_line(f"[*] Cola guardada en {path}\n", "info")
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo guardar la cola:\n{e}")

    def _load_queue(self):
        initial_dir = self.dest_var.get().strip() or os.path.expanduser("~")
        path = filedialog.askopenfilename(
            title="Cargar cola", initialdir=initial_dir,
            filetypes=[("Texto", "*.txt"), ("Todos los archivos", "*.*")],
        )
        if not path: return
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            messagebox.showerror("Error al cargar", f"No se pudo leer la cola:\n{e}")
            return
        added = self._add_urls(extract_urls(content))
        if added:
            self._log_line(f"[*] Cargadas {added} URL(s) desde {path}.\n", "info")
        else:
            messagebox.showinfo("Sin URLs", "No se encontraron URLs nuevas.")

    # ── MENÚ PLANTILLA ───────────────────────────────────────

    def _open_template_menu(self):
        if not getattr(self, "template_menu", None):
            return
        try:
            x = self.template_btn.winfo_rootx()
            y = self.template_btn.winfo_rooty() + self.template_btn.winfo_height()
            self.template_menu.tk_popup(x, y)
        finally:
            self.template_menu.grab_release()

    def _set_template(self, template):
        self.template_var.set(template)
        if getattr(self, "template_entry", None):
            try: self.template_entry.event_generate("<FocusOut>")
            except Exception: pass
        self._log_line(f"[*] Plantilla: {template}\n", "info")

    def _validate_template(self):
        template = (self.template_var.get() or "").strip()
        self.template_var.set(template)
        if not template:
            messagebox.showerror("Plantilla inválida",
                                 "La plantilla de salida no puede estar vacía.")
            return False
        if "\0" in template:
            messagebox.showerror("Plantilla inválida",
                                 "La plantilla contiene caracteres no permitidos.")
            return False
        if os.name == "nt":
            for ch in '<>"|?*':
                if ch in template:
                    messagebox.showerror("Plantilla inválida",
                                         f"El carácter '{ch}' no es válido en Windows.")
                    return False
            for idx, ch in enumerate(template):
                if ch == ":" and not (idx == 1 and template[0].isalpha()):
                    messagebox.showerror("Plantilla inválida",
                                         "':' solo se permite tras la letra de unidad.")
                    return False
        return True

    # ── LOG ──────────────────────────────────────────────────

    def _ensure_log_file(self):
        if self.log_file_path: return
        logs_dir = CONFIG_PATH.parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        self.log_file_path = logs_dir / f"{today}.txt"
        if not self.log_file_path.exists():
            self.log_file_path.write_text("", encoding="utf-8")

    def _log_line(self, text, tag=None):
        ts = datetime.now().strftime("%H:%M:%S")
        if tag is None:
            if   text.startswith(("[ERROR]", "[!]")):       tag = "error"
            elif text.startswith("[OK]"):                   tag = "ok"
            elif text.startswith(("[*]", "[+]", "[+DnD]")): tag = "info"
            elif text.startswith("$"):                      tag = "cmd"
            else:                                           tag = "default"
        self.log.insert("end", f"[{ts}] ", "ts")
        self.log.insert("end", text, tag)
        self.log.see("end")
        try:
            self._ensure_log_file()
            with self.log_file_path.open("a", encoding="utf-8") as fh:
                fh.write(f"[{ts}] {text}")
        except Exception:
            pass

    # ── DEPENDENCIAS ─────────────────────────────────────────

    def _check_dependencies(self):
        for name, cmd, critical, hint in [
            ("yt-dlp", [YTDLP_CMD, "--version"], True,  "Instala 'yt-dlp'."),
            ("ffmpeg", ["ffmpeg", "-version"],  True,  "Instala 'ffmpeg'."),
        ]:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        check=False, timeout=5)
            except FileNotFoundError:
                self._log_line(f"[ERROR] No se encontró '{name}'. {hint}\n", "error")
                if critical:
                    messagebox.showerror("Dependencia faltante",
                                         f"No se encontró '{name}'.\n{hint}")
                if name == "yt-dlp": self.ytdlp_available = False
                if name == "ffmpeg": self.ffmpeg_available = False
                continue
            except Exception as exc:
                self._log_line(f"[ADVERTENCIA] No pude ejecutar '{name}': {exc}\n", "error")
                continue
            output     = result.stdout.strip() or result.stderr.strip()
            first_line = output.splitlines()[0] if output else f"rc={result.returncode}"
            self._log_line(f"[*] {name} → {first_line}\n", "info")
            if name == "yt-dlp":
                self.sb_ytdlp_var.set(f"yt-dlp {first_line.strip()}")
        try:
            aria = subprocess.run(["aria2c", "--version"], capture_output=True,
                                  text=True, check=False, timeout=5)
            if aria.returncode == 0:
                line = (aria.stdout.strip().splitlines()[0]
                        if aria.stdout else "aria2c disponible")
                self._log_line(f"[*] aria2c → {line}\n", "info")
            else:
                self.aria2_available = False
                self._log_line("[ADVERTENCIA] aria2c respondió con error.\n", "error")
        except FileNotFoundError:
            self.aria2_available = False
            self._log_line("[AVISO] aria2c no disponible; variante externa desactivada.\n")

    def _open_logs_dir(self):
        logs_dir = CONFIG_PATH.parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        try:
            if   sys.platform.startswith("darwin"): subprocess.Popen(["open",     str(logs_dir)])
            elif os.name == "nt":                   os.startfile(str(logs_dir))
            else:                                   subprocess.Popen(["xdg-open", str(logs_dir)])
        except Exception as exc:
            messagebox.showerror("Error", f"No pude abrir logs:\n{exc}")

    # ── ARGS / PRESETS ───────────────────────────────────────

    def _join_tokens(self, tokens):
        if not tokens: return ""
        try:    return shlex.join(tokens)
        except: return " ".join(shlex.quote(t) for t in tokens)

    def _parse_extra_args(self):
        current = (self.extra_args_var.get() or "").strip()
        if not current: return []
        try:    return shlex.split(current)
        except: return current.split()

    def _apply_extra_args_delta(self, add_tokens=None, remove_tokens=None, preview=False):
        add_tokens    = list(add_tokens    or [])
        remove_tokens = list(remove_tokens or [])
        tokens        = self._parse_extra_args()

        for token in remove_tokens:
            while token in tokens:
                idx = tokens.index(token)
                tokens.pop(idx)
                if token in self.ARG_FLAGS_WITH_VALUE and idx < len(tokens):
                    tokens.pop(idx)

        def _rm_flag(flag, pool):
            while flag in pool:
                fi = pool.index(flag)
                pool.pop(fi)
                if flag in self.ARG_FLAGS_WITH_VALUE and fi < len(pool):
                    pool.pop(fi)

        i = 0
        while i < len(add_tokens):
            token = add_tokens[i]
            if token in self.ARG_FLAGS_WITH_VALUE:
                value = add_tokens[i + 1] if i + 1 < len(add_tokens) else ""
                _rm_flag(token, tokens)
                tokens.extend([token, value])
                i += 2; continue
            if token not in tokens: tokens.append(token)
            i += 1

        new_string = self._join_tokens(tokens)
        if preview: return new_string
        self.extra_args_var.set(new_string)
        return new_string

    def _apply_avoid_dash(self):
        before     = (self.extra_args_var.get() or "").strip()
        new_string = self._apply_extra_args_delta(self.AVOID_DASH_TOKENS, preview=True)
        if new_string == before:
            messagebox.showinfo("Evitar DASH", "Parámetros ya aplicados en Args extra.")
            return
        self._apply_extra_args_delta(self.AVOID_DASH_TOKENS)
        self._log_line("[*] Parámetros No-DASH añadidos.\n", "info")

    def _apply_preset(self):
        if (self.browser_var.get() or "none").lower() == "none":
            self.browser_var.set("firefox")
        pieces = [
            "--retries", "infinite", "--fragment-retries", "infinite",
            "--concurrent-fragments", "1", "-4",
            "--user-agent", "Mozilla/5.0",
            "--extractor-args", "youtube:player_client=web,ssap=ignore",
        ]
        before = (self.extra_args_var.get() or "").strip()
        new_string = self._apply_extra_args_delta(pieces, preview=True)
        if new_string == before:
            messagebox.showinfo("Anti-403", "Preset ya aplicado en Args extra.")
            return
        self._apply_extra_args_delta(pieces)
        self._log_line(
            f"[*] Preset anti-403 aplicado. Cookies: {self.browser_var.get()}.\n", "info")

    def _consider_make_default(self, attempts, variant_idx):
        if variant_idx is None or variant_idx <= 0: return
        try:    variant = attempts[variant_idx]
        except: return
        add_tokens    = variant.get("delta_add",    [])
        remove_tokens = variant.get("delta_remove", [])
        if not add_tokens and not remove_tokens: return
        current = (self.extra_args_var.get() or "").strip()
        updated = self._apply_extra_args_delta(add_tokens, remove_tokens, preview=True)
        if updated == current: return
        if not messagebox.askyesno("Hacer predeterminada",
                                   "Esta descarga usó variante avanzada.\n"
                                   "¿Copiar parámetros a Args extra?"):
            return
        self._apply_extra_args_delta(add_tokens, remove_tokens)
        self.cfg["extra_args"] = self.extra_args_var.get().strip()
        save_config(self.cfg)
        self._log_line("[*] Variante fijada como predeterminada.\n", "info")

    # ── CONFIG ───────────────────────────────────────────────

    def _save_options(self):
        try:
            q = str(int(self.quality_var.get()))
            if not (0 <= int(q) <= 9): raise ValueError
        except Exception:
            messagebox.showerror("Error", "Calidad debe ser un entero 0–9.")
            return
        if not self._validate_template(): return
        self.cfg.update({
            "download_dir":    self.dest_var.get().strip(),
            "audio_quality":   q,
            "audio_format":    self.format_var.get().strip(),
            "extra_args":      self.extra_args_var.get().strip(),
            "browser_cookies": self.browser_var.get().strip(),
            "cookies_file":    self.cookies_file_var.get().strip(),
            "output_template": self.template_var.get().strip(),
            "playlist":        self.playlist_var.get(),
        })
        save_config(self.cfg)
        self._log_line("[*] Opciones guardadas.\n", "info")

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.dest_var.get())
        if d:
            self.dest_var.set(d)
            self.sb_dest_var.set(f"Destino: {d}")

    def _choose_cookies_file(self):
        current = self.cookies_file_var.get().strip()
        initial_dir = ""
        if current:
            initial_dir = (current if os.path.isdir(current)
                           else os.path.dirname(current))
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = self.dest_var.get().strip() or os.path.expanduser("~")
        path = filedialog.askopenfilename(
            title="Seleccionar cookies.txt", initialdir=initial_dir,
            filetypes=[("cookies.txt", "*.txt"), ("Todos los archivos", "*.*")],
        )
        if path:
            if not os.path.isfile(path):
                messagebox.showerror("No encontrado", f"No existe:\n{path}")
                return
            self.cookies_file_var.set(path)
            if getattr(self, "cookies_entry", None):
                try: self.cookies_entry.event_generate("<FocusOut>")
                except Exception: pass

    # ── COMANDOS DE DESCARGA ─────────────────────────────────

    def _build_cmd_template(self):
        fmt      = self.format_var.get().strip()   or "mp3"
        q        = self.quality_var.get().strip()  or "0"
        template = self.template_var.get().strip() or "%(title)s.%(ext)s"
        cmd = [
            YTDLP_CMD, "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", fmt,
            "--audio-quality", q,
            "--embed-thumbnail", "--embed-metadata",
            "-o", template,
        ]
        browser      = (self.browser_var.get().strip().lower() or "none")
        cookies_file = self.cookies_file_var.get().strip()
        if cookies_file:
            cmd.extend(["--cookies", cookies_file])
            self._log_line("[*] Usando cookies desde archivo.\n", "info")
        elif browser != "none":
            cmd.extend(["--cookies-from-browser", browser])
            self._log_line(f"[*] Cookies desde navegador: {browser}\n", "info")
        user_args = (self.extra_args_var.get().strip()
                     if hasattr(self, "extra_args_var") else "")
        # No forzamos player_client — yt-dlp elige el mejor disponible automáticamente
        if DENO_RUNTIME_ARG:
            cmd.extend(DENO_RUNTIME_ARG)
        if user_args:
            cmd.extend(shlex.split(user_args))
        if self.playlist_var.get():
            cmd.extend(["--yes-playlist", "--ignore-errors"])
        else:
            cmd.extend(["--no-playlist"])
        return cmd

    def _build_attempts(self, base_cmd):
        attempts = []

        def add_v(cmd, add=None, rm=None):
            attempts.append({"cmd": cmd,
                              "delta_add":    list(add or []),
                              "delta_remove": list(rm  or [])})

        add_v(list(base_cmd))
        dash   = ["-f", "bestaudio[protocol!=http_dash_segments]/bestaudio"]
        chunk  = dash   + ["--http-chunk-size", "10M"]
        prefer = chunk  + ["--hls-prefer-ffmpeg"]
        web    = prefer + ["--extractor-args", "youtube:player_client=web,ssap=ignore",
                           "--user-agent", "Mozilla/5.0"]
        aria   = web    + ["--external-downloader", "aria2c",
                           "--external-downloader-args", "-x2 -k1M"]
        add_v(list(base_cmd) + dash,   dash)
        add_v(list(base_cmd) + chunk,  chunk)
        add_v(list(base_cmd) + prefer, prefer)
        add_v(list(base_cmd) + web,    web)
        if "-4" in base_cmd:
            v = [x for x in base_cmd if x != "-4"]
            add_v(v + web, web, ["-4"])
        if self.aria2_available:
            add_v(list(base_cmd) + aria, aria)
        return attempts

    def _stop_all(self):
        self._dl_stop_requested = True
        while True:
            try: self.download_queue.get_nowait()
            except queue.Empty: break
        for t in list(self.dl_threads):
            try: t.stop()
            except Exception: pass
        self.start_btn.configure(state="normal")
        try: self.start_btn_tb.configure(state="normal")
        except Exception: pass
        self._log_line("[*] Descargas detenidas por el usuario.\n", "info")
        self._update_statusbars()

    def _start_downloads(self):
        outdir = self.dest_var.get().strip()
        if not outdir:
            messagebox.showerror("Error", "Selecciona carpeta de destino.")
            return
        Path(outdir).mkdir(parents=True, exist_ok=True)
        if not self.urls:
            messagebox.showinfo("Cola vacía", "Añade alguna URL primero.")
            return
        if not self._validate_template():
            return

        self._dl_stop_requested = False
        base_cmd = self._build_cmd_template()
        attempts = self._build_attempts(base_cmd)
        self._log_line(f"[DEBUG] CMD base: {' '.join(base_cmd)}\n", "cmd")

        for url in list(self.urls):
            self.download_queue.put(url)
            self._set_item_status(url, "pending")

        self.start_btn.configure(state="disabled")
        try: self.start_btn_tb.configure(state="disabled")
        except Exception: pass

        self.sb_dest_var.set(f"Destino: {outdir}")
        self._log_line(f"== Inicio de descargas ({len(self.urls)} en cola) ==\n", "info")

        def next_download():
            if self.active_dl is not None:
                return
            if self._dl_stop_requested:
                self._dl_stop_requested = False
                self.start_btn.configure(state="normal")
                try: self.start_btn_tb.configure(state="normal")
                except Exception: pass
                return
            try:
                url = self.download_queue.get_nowait()
            except queue.Empty:
                self.start_btn.configure(state="normal")
                try: self.start_btn_tb.configure(state="normal")
                except Exception: pass
                self._log_line("== Todo descargado ==\n", "ok")
                self._update_statusbars()
                return

            def done_cb(thread_obj, success, variant_idx):
                self.dl_threads.discard(thread_obj)
                self.active_dl = None
                def apply_st():
                    sub_id = self._playlist_current_sub.pop(url, None)
                    if sub_id:
                        self.canvas_queue.update_item(sub_id,
                            status="ok" if success else "error",
                            progress=100.0, speed="—", eta="—")
                    self._set_item_status(url, "ok" if success else "error")
                    if success:
                        self._consider_make_default(attempts, variant_idx)
                self.after(0, apply_st)
                self.after(100, next_download)

            dl = Downloader(url, outdir, attempts, self.log_queue, done_cb)
            self._set_item_status(url, "downloading")
            self.active_dl = dl
            self.dl_threads.add(dl)
            dl.start()
            self._update_statusbars()

        next_download()

    def _drain_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    kind, *payload = item
                    if kind == "progress":
                        url, percent = payload
                        sub_id = self._playlist_current_sub.get(url)
                        if sub_id:
                            self.canvas_queue.update_item(sub_id, progress=float(percent))
                        elif url in self.urls:
                            self.progress[url] = percent
                            if self.item_status.get(url) != "downloading":
                                self._set_item_status(url, "downloading")
                            else:
                                self._refresh_item_display(url)
                    elif kind == "progress_detailed":
                        url, info = payload
                        sub_id = self._playlist_current_sub.get(url)
                        if sub_id:
                            kw = {"progress": float(info.percent) if info.percent is not None else 0}
                            if info.speed: kw["speed"] = info.speed
                            if info.eta:   kw["eta"]   = info.eta
                            if info.size:  kw["size"]  = info.size
                            self.canvas_queue.update_item(sub_id, **kw)
                            if info.speed:
                                self.sb_dest_var.set(f"↓ {info.speed} · {self.dest_var.get().strip()}")
                        elif url in self.urls:
                            self.progress_details[url] = info
                            if info.percent is not None:
                                self.progress[url] = int(info.percent)
                            if self.item_status.get(url) != "downloading":
                                self._set_item_status(url, "downloading")
                            else:
                                self._refresh_item_display(url)
                            if info.item_current is not None:
                                ex = self.progress_details.get(url)
                                if ex:
                                    ex.item_current = info.item_current
                                    ex.item_total   = info.item_total
                                self._refresh_item_display(url)
                            if info.speed:
                                self.sb_dest_var.set(
                                    f"↓ {info.speed} · {self.dest_var.get().strip()}")
                    elif kind == "playlist_sub_start":
                        parent_url, item_num, item_total = payload
                        # Mark previous sub-item as done
                        prev_sub = self._playlist_current_sub.get(parent_url)
                        if prev_sub:
                            self.canvas_queue.update_item(prev_sub, status="ok",
                                                          progress=100.0, speed="—", eta="—")
                        # Create new sub-item row
                        sub_id = f"__sub__{item_num}__{parent_url}"
                        self._playlist_current_sub[parent_url] = sub_id
                        self._playlist_sub_count[parent_url]   = item_total
                        self.canvas_queue.add_item({
                            "id":       sub_id,
                            "name":     f"  [{item_num}/{item_total}] Cargando...",
                            "size":     "—",
                            "progress": 0.0,
                            "speed":    "—",
                            "eta":      "—",
                            "status":   "downloading",
                        })
                        # Update parent row
                        if parent_url in self.urls:
                            self.canvas_queue.update_item(parent_url,
                                name=f"Playlist [{item_num}/{item_total}]",
                                status="downloading")
                    elif kind == "playlist_sub_title":
                        parent_url, title = payload
                        sub_id = self._playlist_current_sub.get(parent_url)
                        if sub_id:
                            self.canvas_queue.update_item(sub_id, name=f"  ♪ {title}")
                    continue
                line = item
                tag  = None
                if   line.startswith(("[ERROR]", "[!]")):  tag = "error"
                elif line.startswith("[OK]"):               tag = "ok"
                elif line.startswith(("[*]", "[+]")):       tag = "info"
                elif line.startswith("$"):                  tag = "cmd"
                self._log_line(line, tag)
        except queue.Empty:
            pass
        self.after(80, self._drain_log_queue)

    def _auto_save_queue(self):
        try:
            entries = [
                {"url": u, "status": self.item_status.get(u, "pending")}
                for u in self.urls
                if not u.startswith("__sub__")
            ]
            data = {"saved_at": datetime.now().isoformat(), "entries": entries}
            QUEUE_SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
            QUEUE_SAVE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _auto_load_queue(self):
        if not QUEUE_SAVE_PATH.exists():
            return
        try:
            data    = json.loads(QUEUE_SAVE_PATH.read_text(encoding="utf-8"))
            entries = data.get("entries", [])
            if not entries:
                return
            n_ok = n_pend = n_err = 0
            for entry in entries:
                url    = entry.get("url", "").strip()
                status = entry.get("status", "pending")
                if not url or url in self.urls:
                    continue
                self.urls.append(url)
                self.item_status[url] = status
                pct = 100.0 if status == "ok" else 0.0
                self.progress[url] = pct if status != "ok" else None
                self.canvas_queue.add_item({
                    "id":       url,
                    "name":     self._short_name(url),
                    "size":     "—",
                    "progress": pct,
                    "speed":    "—",
                    "eta":      "—",
                    "status":   status,
                })
                if   status == "ok":    n_ok   += 1
                elif status == "error": n_err  += 1
                else:                   n_pend += 1
            self._update_statusbars()
            parts = []
            if n_pend: parts.append(f"{n_pend} pendiente{'s' if n_pend>1 else ''}")
            if n_ok:   parts.append(f"{n_ok} completada{'s' if n_ok>1 else ''}")
            if n_err:  parts.append(f"{n_err} con error")
            if parts:
                self._log_line(f"[*] Cola restaurada: {', '.join(parts)}.\n", "info")
        except Exception:
            pass

    def destroy(self):
        self._auto_save_queue()
        for t in list(self.dl_threads):
            try: t.stop()
            except Exception: pass
        super().destroy()


# ============================================================
#  MAIN
# ============================================================

def main():
    if sys.platform != "win32":
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
