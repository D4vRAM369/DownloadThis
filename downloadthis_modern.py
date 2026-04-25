#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
downloadthis_modern — GUI mejorada para yt-dlp (audio)

Cambios:
- Añadido bloque de "requirements" que intenta instalar automáticamente
  las dependencias Python necesarias (ttkbootstrap, tkinterdnd2, yt-dlp)
  en el entorno actual (venv o sistema).
- Arreglado el crash cuando NO está ttkbootstrap instalado, haciendo que
  el parámetro bootstyle se ignore de forma segura en tkinter.ttk.
"""

import os, re, sys, json, queue, shlex, signal, subprocess, threading
from pathlib import Path
import importlib
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

# ============================================================
#  BLOQUE DE REQUIREMENTS: auto-instalar dependencias Python
# ============================================================

def ensure_python_packages():
    """
    Intenta asegurar que ciertos módulos de Python están instalados.
    - Si falta un módulo, llama a `pip install` dentro del mismo intérprete.
    - No aborta el script si la instalación falla: solo muestra el error.
    """
    required = {
        # módulo -> nombre en pip
        "ttkbootstrap": "ttkbootstrap",
        "tkinterdnd2": "tkinterdnd2",
        "yt_dlp": "yt-dlp",  # proporciona el binario `yt-dlp`
    }

    for module_name, pip_name in required.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            try:
                print(f"[SETUP] Instalando dependencia '{pip_name}'…")
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pip_name]
                )
                print(f"[SETUP] '{pip_name}' instalado correctamente.")
            except Exception as exc:
                # No rompemos el programa, solo avisamos.
                print(f"[SETUP] No se pudo instalar '{pip_name}': {exc}")

# Ejecutamos el asegurador de dependencias lo antes posible
ensure_python_packages()

# ============================================================
#  IMPORTS CONDICIONALES: ttkbootstrap y tkinterdnd2
# ============================================================

# ===== Intentar importar ttkbootstrap =====
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter.ttk as ttk
    TTKBOOTSTRAP_AVAILABLE = False

    # Parche: hacer que los widgets de tkinter.ttk ignoren el parámetro `bootstyle`
    def _wrap_bootstyle(cls):
        orig_init = cls.__init__
        def __init__(self, *args, **kwargs):
            # Si alguien pasa bootstyle en un entorno sin ttkbootstrap, lo quitamos.
            kwargs.pop("bootstyle", None)
            return orig_init(self, *args, **kwargs)
        cls.__init__ = __init__
        return cls

    ttk.Label      = _wrap_bootstyle(ttk.Label)
    ttk.Button     = _wrap_bootstyle(ttk.Button)
    ttk.Checkbutton = _wrap_bootstyle(ttk.Checkbutton)
    ttk.Labelframe = _wrap_bootstyle(ttk.Labelframe)

# ===== DnD opcional (tkinterdnd2) =====
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES, DND_TEXT
    DND_AVAILABLE = True
except Exception:
    TkinterDnD = None
    DND_FILES = None
    DND_TEXT = None
    DND_AVAILABLE = False

# ===== URL extractor estricto =====
STRICT_URL_RE = re.compile(
    r"""(?ix)
    \b(
      (?:https?://|www\.)                # esquema o www.
      [a-z0-9][a-z0-9.-]+\.[a-z]{2,}     # dominio.tld
      (?:/[^\s<>"']*)?                   # ruta opcional
    )
    """
)
YTSEARCH_RE = re.compile(r'(?i)\bytsearch(?::\d+)?\s*:[^\s].+')
PROGRESS_RE = re.compile(r"^\[download\]\s+(\d{1,3}(?:\.\d+)?)%")

# ===== Parsers avanzados para feedback visual =====
PROGRESS_DETAIL_RE = re.compile(
    r'^\[download\]\s+(\d{1,3}(?:\.\d+)?)%\s+of\s+([^\s]+)\s+at\s+([^\s]+)\s+ETA\s+([^\s]+)'
)
SPEED_RE = re.compile(r'at\s+([0-9.]+[KMGT]?i?B/s)')
ETA_RE = re.compile(r'ETA\s+(\d{2}:\d{2}|\d+:\d{2}:\d{2})')
SIZE_RE = re.compile(r'(\d+(?:\.\d+)?[KMGT]?i?B)')
PLAYLIST_INDEX_RE = re.compile(r'\[download\] Downloading video (\d+) of (\d+)')

class DownloadProgress:
    """Clase para almacenar información detallada del progreso"""
    def __init__(self, percent=None, size=None, speed=None, eta=None, item_current=None, item_total=None):
        self.percent = percent
        self.size = size
        self.speed = speed
        self.eta = eta
        self.item_current = item_current
        self.item_total = item_total

    def __str__(self):
        parts = []
        if self.percent is not None:
            parts.append(f"{self.percent}%")
        if self.speed:
            parts.append(f"{self.speed}")
        if self.eta:
            parts.append(f"ETA {self.eta}")
        if self.item_current and self.item_total:
            parts.append(f"[{self.item_current}/{self.item_total}]")
        return " • ".join(parts) if parts else "Descargando..."

def parse_progress_line(line: str) -> DownloadProgress:
    if not line.startswith('[download]'):
        return None
    match = PROGRESS_DETAIL_RE.match(line.strip())
    if match:
        percent = float(match.group(1))
        size = match.group(2)
        speed = match.group(3)
        eta = match.group(4)
        return DownloadProgress(percent, size, speed, eta)
    percent = None
    match = PROGRESS_RE.match(line.strip())
    if match:
        percent = float(match.group(1))
    speed = None
    match = SPEED_RE.search(line)
    if match:
        speed = match.group(1)
    eta = None
    match = ETA_RE.search(line)
    if match:
        eta = match.group(1)
    if percent is not None or speed or eta:
        return DownloadProgress(percent, None, speed, eta)
    match = PLAYLIST_INDEX_RE.search(line)
    if match:
        return DownloadProgress(item_current=int(match.group(1)), item_total=int(match.group(2)))
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

CONFIG_PATH = Path.home() / ".config" / "downloadthis" / "config.json"

def ensure_config():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg = {
        "download_dir": str(Path.home() / "Descargas"),
        "audio_quality": "0",
        "audio_format": "mp3",
        "cookies_file": "",
        "extra_args": "",
        "browser_cookies": "none",
        "output_template": "%(title)s.%(ext)s",
        "playlist": False,
    }
    if CONFIG_PATH.exists():
        try:
            on_disk = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update(on_disk)
        except Exception:
            pass
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg

def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def format_download_error(error, context="descarga"):
    error_messages = {
        'TimeoutError': {'message': f'Tiempo de espera agotado durante {context}', 'suggestion': 'Verifica tu conexión a internet'},
        'ConnectionError': {'message': f'Error de conexión durante {context}', 'suggestion': 'Comprueba tu conexión a internet'},
        'URLError': {'message': f'URL no válida o inaccesible', 'suggestion': 'Verifica que la URL esté correcta'},
        'PermissionError': {'message': f'Sin permisos para escribir en el destino', 'suggestion': 'Elige otra carpeta de destino'},
        'FileNotFoundError': {'message': f'Herramienta requerida no encontrada', 'suggestion': 'Instala las dependencias faltantes (yt-dlp, ffmpeg)'},
        'OSError': {'message': f'Error del sistema operativo', 'suggestion': 'Verifica permisos y espacio en disco'},
        'subprocess.TimeoutExpired': {'message': f'Proceso cancelado por timeout (>30min)', 'suggestion': 'La descarga era muy lenta. Prueba con otra URL'}
    }
    error_type = type(error).__name__
    error_info = error_messages.get(error_type, {'message': f'Error inesperado: {str(error)[:100]}', 'suggestion': 'Revisa el log para más detalles'})
    return f"[ERROR] {error_info['message']}\n[TIP] {error_info['suggestion']}\n"

class Downloader(threading.Thread):
    def __init__(self, url, outdir, attempts, log_queue, done_callback):
        super().__init__(daemon=True)
        self.url = url
        self.outdir = outdir
        self.attempts = attempts
        self.log_queue = log_queue
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
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            for raw_line in self.proc.stdout:
                if self._stop.is_set():
                    break
                line = raw_line.lstrip("\r")
                if "HTTP Error 413" in line or "Request Entity Too Large" in line:
                    saw_413 = True
                progress_info = parse_progress_line(line.strip())
                if progress_info and progress_info.percent is not None:
                    self.log_queue.put(("progress_detailed", self.url, progress_info))
                    try:
                        percent_val = int(float(progress_info.percent))
                        self.log_queue.put(("progress", self.url, percent_val))
                    except (ValueError, TypeError):
                        pass
                self.log_queue.put(line)
            rc = self.proc.wait()
            return rc, saw_413
        except Exception as e:
            self.log_queue.put(format_download_error(e, "ejecución de yt-dlp"))
            return 1, saw_413

    def run(self):
        self._success = False
        try:
            total = len(self.attempts)
            for idx, variant in enumerate(self.attempts):
                display_idx = idx + 1
                self._variant_index = idx
                cmd_tokens = variant["cmd"] if isinstance(variant, dict) else variant
                self.log_queue.put(f"[*] Intento {display_idx}/{total}…\n")
                rc, saw_413 = self._run_one(cmd_tokens)
                if rc == 0 and not saw_413:
                    self.log_queue.put(f"[OK] Descarga completada: {self.url}\n")
                    self._success = True
                    break
                else:
                    motivo = "detectado 413" if saw_413 else f"rc={rc}"
                    self.log_queue.put(f"[!] Falló intento {display_idx} ({motivo}). Probando variante siguiente…\n")
            else:
                self.log_queue.put(f"[ERROR] Agotadas variantes para: {self.url}\n")
        finally:
            self.done_callback(self, self._success, self._variant_index)

    def stop(self):
        self._stop.set()
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass

# Determinar clase base
if DND_AVAILABLE:
    BaseTk = TkinterDnD.Tk
else:
    BaseTk = tk.Tk

class App(BaseTk):
    ARG_FLAGS_WITH_VALUE = {"-f", "--http-chunk-size", "--extractor-args", "--user-agent", "--external-downloader", "--external-downloader-args"}
    AVOID_DASH_TOKENS = ["-f", "bestaudio[protocol!=http_dash_segments]/bestaudio", "--http-chunk-size", "10M", "--hls-prefer-ffmpeg"]

    def __init__(self):
        super().__init__()
        
        # ===== Configuración de Tema =====
        if TTKBOOTSTRAP_AVAILABLE:
            # Usamos un tema moderno por defecto
            self.style = ttk.Style(theme="cosmo") 
        else:
            self.style = ttk.Style()
            self.style.theme_use('clam') # Fallback decente
        
        self.title("DownloadThis — Pro")
        self.geometry("950x700")
        self.minsize(850, 600)

        self.cfg = ensure_config()
        self.clipboard_last = ""; self.urls = []
        self.item_status = {}
        self.progress = {}
        self.download_queue = queue.Queue(); self.log_queue = queue.Queue()
        self.active_dl = None; self.dl_threads = set()
        self.ytdlp_available = True; self.ffmpeg_available = True; self.aria2_available = True
        self.log_file_path = None

        self._build_ui()
        self._setup_dnd_if_available()
        self.after(800, self._poll_clipboard)
        self.after(80, self._drain_log_queue)
        self._check_dependencies()
        self._bind_shortcuts()

        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                self._add_urls_from_text(arg)

    def _build_ui(self):
        # Contenedor principal con padding
        main_container = ttk.Frame(self, padding=20)
        main_container.pack(fill="both", expand=True)

        # --- Header ---
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill="x", pady=(0, 15))
        
        title_font = ("Helvetica", 18, "bold") if not TTKBOOTSTRAP_AVAILABLE else ("Helvetica", 18)
        ttk.Label(header_frame, text="DownloadThis", font=title_font, bootstyle="primary").pack(side="left")
        ttk.Label(header_frame, text="  |  GUI para yt-dlp", foreground="gray").pack(side="left", pady=(4,0))

        # --- Zona Superior: Destino y Acciones Rápidas ---
        top_card = ttk.Labelframe(main_container, text="Configuración Rápida", padding=10)
        top_card.pack(fill="x", pady=(0, 15))

        self.dest_var = tk.StringVar(value=self.cfg.get("download_dir", str(Path.home() / "Descargas")))
        
        # Grid layout para top_card
        ttk.Label(top_card, text="Destino:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        entry_dest = ttk.Entry(top_card, textvariable=self.dest_var)
        entry_dest.grid(row=0, column=1, sticky="ew", padx=5)
        top_card.columnconfigure(1, weight=1) # El entry se expande
        
        btn_browse = ttk.Button(top_card, text="📂", width=3, command=self._choose_dir, bootstyle="secondary-outline")
        btn_browse.grid(row=0, column=2, padx=5)

        # Botones de acción rápida
        action_frame = ttk.Frame(top_card)
        action_frame.grid(row=0, column=3, padx=(15, 0))
        
        ttk.Button(action_frame, text="Pegar Clipboard", command=self._paste_from_clipboard, bootstyle="info-outline").pack(side="left", padx=2)
        ttk.Button(action_frame, text="+ URL", command=self._add_single_url_dialog, bootstyle="info-outline").pack(side="left", padx=2)

        # --- Zona Central: PanedWindow (Cola | Opciones) ---
        paned = ttk.Panedwindow(main_container, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=(0, 15))

        # Panel Izquierdo: Cola
        left_panel = ttk.Frame(paned)
        paned.add(left_panel, weight=2) # Más espacio a la cola

        lbl_queue = ttk.Label(left_panel, text="Cola de Descargas", font=("Helvetica", 11, "bold"))
        lbl_queue.pack(anchor="w", pady=(0, 5))

        # Listbox con Scrollbar
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, borderwidth=0, highlightthickness=0, font=("Consolas", 10))
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)

        # DnD hint
        hint = "⬇ Arrastra enlaces aquí" if DND_AVAILABLE else "Drag&drop no disponible"
        self.dnd_label = ttk.Label(left_panel, text=hint, foreground="gray", font=("Helvetica", 9))
        self.dnd_label.pack(anchor="w", pady=(5, 5))

        # Botones de control de cola
        queue_btns = ttk.Frame(left_panel)
        queue_btns.pack(fill="x")
        ttk.Button(queue_btns, text="Eliminar", command=self._remove_selected, bootstyle="danger-link").pack(side="left")
        ttk.Button(queue_btns, text="Limpiar Todo", command=self._clear_list, bootstyle="danger-link").pack(side="left", padx=5)
        
        # Spacer
        ttk.Frame(queue_btns).pack(side="left", fill="x", expand=True)
        
        ttk.Button(queue_btns, text="💾 Guardar", command=self._save_queue, bootstyle="link").pack(side="left")
        ttk.Button(queue_btns, text="📂 Cargar", command=self._load_queue, bootstyle="link").pack(side="left")


        # Panel Derecho: Opciones
        right_panel = ttk.Frame(paned, padding=(15, 0, 0, 0))
        paned.add(right_panel, weight=1)

        opt_frame = ttk.Labelframe(right_panel, text="Opciones Avanzadas", padding=10)
        opt_frame.pack(fill="x", anchor="n")

        self.quality_var = tk.StringVar(value=self.cfg.get("audio_quality", "0"))
        self.format_var  = tk.StringVar(value=self.cfg.get("audio_format",  "mp3"))
        self.browser_var = tk.StringVar(value=self.cfg.get("browser_cookies", "none"))
        self.template_var = tk.StringVar(value=self.cfg.get("output_template", "%(title)s.%(ext)s"))
        self.playlist_var = tk.BooleanVar(value=self.cfg.get("playlist", False))
        self.extra_args_var = tk.StringVar(value=self.cfg.get("extra_args", ""))
        self.cookies_file_var = tk.StringVar(value=self.cfg.get("cookies_file", ""))

        # Grid de opciones
        # Fila 0: Formato y Calidad
        ttk.Label(opt_frame, text="Formato:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Combobox(opt_frame, textvariable=self.format_var, values=["mp3", "m4a", "flac", "opus", "wav"], width=8, state="readonly").grid(row=0, column=1, sticky="w", pady=5)
        
        ttk.Label(opt_frame, text="Calidad (0-9):").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(opt_frame, textvariable=self.quality_var, width=5).grid(row=1, column=1, sticky="w", pady=5)

        # Fila 2: Cookies Navegador
        ttk.Label(opt_frame, text="Cookies Nav:").grid(row=2, column=0, sticky="w", pady=5)
        ttk.Combobox(opt_frame, textvariable=self.browser_var, values=["none", "brave", "firefox", "chrome"], width=10, state="readonly").grid(row=2, column=1, sticky="w", pady=5)

        # Fila 3: Cookies Archivo
        ttk.Label(opt_frame, text="Cookies.txt:").grid(row=3, column=0, sticky="w", pady=5)
        cf_frame = ttk.Frame(opt_frame)
        cf_frame.grid(row=3, column=1, sticky="ew")
        self.cookies_entry = ttk.Entry(cf_frame, textvariable=self.cookies_file_var, width=10)
        self.cookies_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(cf_frame, text="...", width=2, command=self._choose_cookies_file, bootstyle="secondary-outline").pack(side="left", padx=(2,0))

        # Fila 4: Plantilla
        ttk.Label(opt_frame, text="Plantilla:").grid(row=4, column=0, sticky="w", pady=5)
        tpl_frame = ttk.Frame(opt_frame)
        tpl_frame.grid(row=4, column=1, sticky="ew")
        self.template_entry = ttk.Entry(tpl_frame, textvariable=self.template_var, width=10)
        self.template_entry.pack(side="left", fill="x", expand=True)
        
        self.template_presets = [
            ("%(title)s.%(ext)s", "%(title)s.%(ext)s"),
            ("%(playlist_index)s - %(title)s.%(ext)s", "%(playlist_index)s - %(title)s.%(ext)s"),
            ("%(uploader)s - %(title)s.%(ext)s", "%(uploader)s - %(title)s.%(ext)s"),
        ]
        self.template_menu = tk.Menu(self, tearoff=False)
        for label, tpl in self.template_presets:
            self.template_menu.add_command(label=label, command=lambda tpl=tpl: self._set_template(tpl))
        
        self.template_btn = ttk.Button(tpl_frame, text="▼", width=2, command=self._open_template_menu, bootstyle="secondary-outline")
        self.template_btn.pack(side="left", padx=(2,0))

        # Fila 5: Args Extra
        ttk.Label(opt_frame, text="Args Extra:").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(opt_frame, textvariable=self.extra_args_var).grid(row=5, column=1, sticky="ew", pady=5)

        # Fila 6: Playlist Checkbox
        ttk.Checkbutton(opt_frame, text="Descargar Playlist", variable=self.playlist_var, bootstyle="round-toggle").grid(row=6, column=0, columnspan=2, sticky="w", pady=10)

        # Botones de herramientas
        tools_frame = ttk.Frame(right_panel)
        tools_frame.pack(fill="x", pady=10)
        ttk.Button(tools_frame, text="Anti-403", command=self._apply_preset, bootstyle="warning-outline", width=10).pack(side="left", padx=2)
        ttk.Button(tools_frame, text="No-DASH", command=self._apply_avoid_dash, bootstyle="warning-outline", width=10).pack(side="left", padx=2)
        
        # --- Botón Principal ---
        self.start_btn = ttk.Button(right_panel, text="DESCARGAR TODO", command=self._start_downloads, bootstyle="success", width=20)
        self.start_btn.pack(pady=10, fill="x")
        
        ttk.Button(right_panel, text="Guardar Config", command=self._save_options, bootstyle="secondary-link").pack()


        # --- Zona Inferior: Logs ---
        log_frame = ttk.Labelframe(main_container, text="Registro de Actividad", padding=5)
        log_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        self.log = tk.Text(log_frame, height=8, wrap="word", font=("Consolas", 9), borderwidth=0, highlightthickness=0)
        self.log.pack(side="left", fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        log_scroll.pack(side="right", fill="y")
        self.log.config(yscrollcommand=log_scroll.set)
        
        self.log.tag_config("error", foreground="#d9534f")
        self.log.tag_config("ok", foreground="#5cb85c")

        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Listo.")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=(10, 2), font=("Helvetica", 9))
        status_bar.pack(fill="x", side="bottom")

    def _setup_dnd_if_available(self):
        if not DND_AVAILABLE:
            return
        try:
            self.listbox.drop_target_register(DND_FILES, DND_TEXT)
            self.listbox.dnd_bind("<<Drop>>", self._on_drop)
            self.dnd_label.configure(text="⬇ Arrastra enlaces o .txt aquí")
        except Exception as exc:
            self._log_line(f"[AVISO] No se pudo activar drag&drop: {exc}\n", "error")

    def _on_drop(self, event):
        data = getattr(event, "data", "") or ""
        parts = [p.strip() for p in re.split(r"[\r\n]+", data) if p.strip()]
        if not parts:
            return
        total = 0
        has_file = False
        for raw in parts:
            if raw.startswith("{") and raw.endswith("}"):
                raw = raw[1:-1]
            p = raw.strip().strip('"').strip("'")
            if not p:
                continue
            if os.path.exists(p):
                has_file = True
                if os.path.isdir(p):
                    continue
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
        if has_file and total:
            self._log_line(f"[+DnD] Añadidas {total} URL(s) de archivo(s).\n")
        elif total:
            self._log_line(f"[+DnD] Añadidas {total} URL(s).\n")

    def _poll_clipboard(self):
        try:
            data = self.clipboard_get()
        except tk.TclError:
            data = ""
        if data != self.clipboard_last:
            self.clipboard_last = data
            found = extract_urls(data)
            if found:
                self.status_var.set(f"Clipboard detectado: {len(found)} URL(s).")
            else:
                self.status_var.set(f"{len(self.urls)} URL(s) en cola.")
        self.after(800, self._poll_clipboard)

    def _bind_shortcuts(self):
        self.bind("<Control-v>", lambda _e: self._paste_from_clipboard())
        self.bind("<Delete>", lambda _e: self._remove_selected())
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
        ttk.Label(win, text="Pega una URL o varias (una por línea):").pack(anchor="w", padx=10, pady=(10, 4))
        txt = tk.Text(win, width=70, height=8)
        txt.pack(padx=10)
        txt.focus_set()
        ttk.Button(
            win,
            text="Añadir",
            command=lambda: (self._add_urls_from_text(txt.get("1.0", "end").strip()), win.destroy())
        ).pack(pady=10)
        win.grab_set()
        self.wait_window(win)

    def _add_urls_from_text(self, text):
        urls = extract_urls(text or "")
        if not urls:
            messagebox.showwarning("Sin URLs", "No se detectaron URLs válidas.")
            return
        added = self._add_urls(urls)
        if added:
            self._log_line(f"[+] Añadidas {added} URL(s).\n")

    def _add_urls(self, urls):
        count = 0
        for u in urls:
            u = u.strip()
            if not u:
                continue
            if u not in self.urls:
                self.urls.append(u)
                self.item_status[u] = "pending"
                self.progress[u] = None
                self.listbox.insert("end", self._format_item_text(u))
                self._refresh_item_display(u)
                count += 1
        self.status_var.set(f"{len(self.urls)} URL(s) en cola.")
        return count

    def _format_item_text(self, url):
        prefix_map = {"pending": "⏳", "downloading": "⬇", "ok": "✓", "error": "✗"}
        state = self.item_status.get(url, "pending")
        prefix = prefix_map.get(state, "•")
        percent = self.progress.get(url)
        pct_text = f" {percent}%" if percent is not None and state == "downloading" else ""
        extra_info = ""
        if state == "downloading" and hasattr(self, 'progress_details'):
            progress_detail = self.progress_details.get(url)
            if progress_detail:
                detail_text = str(progress_detail)
                if progress_detail.speed or progress_detail.eta:
                    extra_info = f" ({detail_text})"
                elif percent is None and progress_detail.percent:
                    pct_text = f" {int(progress_detail.percent)}%"
            if progress_detail and progress_detail.item_current:
                extra_info += f" [Vídeo {progress_detail.item_current}/{progress_detail.item_total}]"
        return f"{prefix}{pct_text}{extra_info} {url}"

    def _refresh_item_display(self, url):
        try:
            idx = self.urls.index(url)
        except ValueError:
            return
        display = self._format_item_text(url)
        current_selection = set(self.listbox.curselection())
        self.listbox.delete(idx)
        self.listbox.insert(idx, display)
        if idx in current_selection:
            self.listbox.selection_set(idx)
        
        # Colores adaptados al tema (si es oscuro, usar colores claros)
        is_dark = False  # Simplificación, idealmente detectar tema
        color_map = {
            "pending": "#666666" if not is_dark else "#aaaaaa",
            "downloading": "#0b63c5" if not is_dark else "#4da3ff",
            "ok": "#1a7f37" if not is_dark else "#5cb85c",
            "error": "#b00020" if not is_dark else "#d9534f",
        }
        state = self.item_status.get(url, "pending")
        fg = color_map.get(state, "#333333")
        try:
            self.listbox.itemconfig(idx, foreground=fg)
        except tk.TclError:
            pass

    def _set_item_status(self, url, state):
        if url not in self.urls:
            return
        self.item_status[url] = state
        if state == "downloading":
            if self.progress.get(url) is None:
                self.progress[url] = 0
        elif state == "pending":
            self.progress[url] = None
        elif state in {"ok", "error"}:
            self.progress.pop(url, None)
        self._refresh_item_display(url)

    def _remove_selected(self):
        sel = list(self.listbox.curselection())
        sel.reverse()
        removed = 0
        for idx in sel:
            if idx >= len(self.urls):
                continue
            url = self.urls.pop(idx)
            self.listbox.delete(idx)
            self.item_status.pop(url, None)
            self.progress.pop(url, None)
            removed += 1
        if removed:
            self._log_line(f"[-] Eliminadas {removed} URL(s).\n")
        self.status_var.set(f"{len(self.urls)} URL(s) en cola.")

    def _clear_list(self):
        self.listbox.delete(0, "end")
        self.urls.clear()
        self.item_status.clear()
        self.progress.clear()
        self.status_var.set("Cola vacía.")
        self._log_line("[*] Cola vaciada.\n")

    def _save_queue(self):
        if not self.urls:
            messagebox.showinfo("Cola vacía", "No hay URLs para guardar.")
            return
        initial_dir = self.dest_var.get().strip() or os.path.expanduser("~")
        path = filedialog.asksaveasfilename(
            title="Guardar cola",
            initialdir=initial_dir,
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Todos los archivos", "*.*")],
            initialfile="downloadthis-queue.txt"
        )
        if not path:
            return
        try:
            Path(path).write_text("\n".join(self.urls) + "\n", encoding="utf-8")
            self._log_line(f"[*] Cola guardada en {path}\n")
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo guardar la cola:\n{e}")

    def _load_queue(self):
        initial_dir = self.dest_var.get().strip() or os.path.expanduser("~")
        path = filedialog.askopenfilename(
            title="Cargar cola",
            initialdir=initial_dir,
            filetypes=[("Texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            messagebox.showerror("Error al cargar", f"No se pudo leer la cola:\n{e}")
            return
        added = self._add_urls(extract_urls(content))
        if added:
            self._log_line(f"[*] Cargadas {added} URL(s) desde {path}.\n")
        else:
            messagebox.showinfo("Sin URLs", "No se encontraron URLs nuevas.")

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
            try:
                self.template_entry.event_generate("<FocusOut>")
            except Exception:
                pass
        self._log_line(f"[*] Plantilla establecida: {template}\n")

    def _validate_template(self):
        template = (self.template_var.get() or "").strip()
        self.template_var.set(template)
        if not template:
            messagebox.showerror("Plantilla inválida", "La plantilla de salida no puede estar vacía.")
            return False
        if "\0" in template:
            messagebox.showerror("Plantilla inválida", "La plantilla contiene caracteres no permitidos.")
            return False
        if os.name == "nt":
            forbidden = '<>"|?*'
            for ch in forbidden:
                if ch in template:
                    messagebox.showerror("Plantilla inválida", f"El carácter '{ch}' no es válido en nombres de archivo de Windows.")
                    return False
            colon_positions = [i for i, ch in enumerate(template) if ch == ":"]
            for idx in colon_positions:
                if not (idx == 1 and template and template[0].isalpha()):
                    messagebox.showerror("Plantilla inválida", "':' solo se permite tras la letra de unidad (ej. C:/ruta).")
                    return False
        return True

    def _ensure_log_file(self):
        if self.log_file_path:
            return
        logs_dir = CONFIG_PATH.parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        self.log_file_path = logs_dir / f"{today}.txt"
        if not self.log_file_path.exists():
            self.log_file_path.write_text("", encoding="utf-8")

    def _check_dependencies(self):
        checks = [
            ("yt-dlp", ["yt-dlp", "--version"], True, "Instala 'yt-dlp'."),
            ("ffmpeg", ["ffmpeg", "-version"], True, "Instala 'ffmpeg'.")
        ]
        for name, cmd, critical, hint in checks:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=5)
            except FileNotFoundError:
                self._log_line(f"[ERROR] No se encontró '{name}'. {hint}\n", "error")
                if critical:
                    messagebox.showerror("Dependencia faltante", f"No se encontró '{name}'.\n{hint}")
                if name == "yt-dlp":
                    self.ytdlp_available = False
                if name == "ffmpeg":
                    self.ffmpeg_available = False
                continue
            except Exception as exc:
                self._log_line(f"[ADVERTENCIA] No pude ejecutar '{name}': {exc}\n", "error")
                continue
            output = result.stdout.strip() or result.stderr.strip()
            first_line = output.splitlines()[0] if output else f"rc={result.returncode}"
            self._log_line(f"[*] {name} → {first_line}\n")
        try:
            aria = subprocess.run(["aria2c", "--version"], capture_output=True, text=True, check=False, timeout=5)
            if aria.returncode == 0:
                line = aria.stdout.strip().splitlines()[0] if aria.stdout else "aria2c disponible"
                self._log_line(f"[*] aria2c → {line}\n")
            else:
                self.aria2_available = False
                self._log_line("[ADVERTENCIA] 'aria2c' respondió con error; omito variante aria2c.\n", "error")
        except FileNotFoundError:
            self.aria2_available = False
            self._log_line("[AVISO] 'aria2c' no está instalado; se desactiva la variante externa (aria2c).\n")

    def _open_logs_dir(self):
        logs_dir = (CONFIG_PATH.parent / "logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("darwin"):
                subprocess.Popen(["open", str(logs_dir)])
            elif os.name == "nt":
                os.startfile(str(logs_dir))
            else:
                subprocess.Popen(["xdg-open", str(logs_dir)])
        except Exception as exc:
            messagebox.showerror("No se pudo abrir", f"No pude abrir la carpeta de logs:\n{exc}")

    def _join_tokens(self, tokens):
        if not tokens:
            return ""
        try:
            return shlex.join(tokens)
        except AttributeError:
            return " ".join(shlex.quote(t) for t in tokens)

    def _parse_extra_args(self):
        current = (self.extra_args_var.get() or "").strip()
        if not current:
            return []
        try:
            return shlex.split(current)
        except ValueError:
            return current.split()

    def _apply_extra_args_delta(self, add_tokens=None, remove_tokens=None, preview=False):
        add_tokens = list(add_tokens or [])
        remove_tokens = list(remove_tokens or [])
        tokens = self._parse_extra_args()

        # Eliminar tokens
        for token in remove_tokens:
            while token in tokens:
                idx = tokens.index(token)
                tokens.pop(idx)
                if token in self.ARG_FLAGS_WITH_VALUE and idx < len(tokens):
                    tokens.pop(idx)

        def _remove_flag_instances(flag, pool):
            while flag in pool:
                f_idx = pool.index(flag)
                pool.pop(f_idx)
                if flag in self.ARG_FLAGS_WITH_VALUE and f_idx < len(pool):
                    pool.pop(f_idx)

        # Añadir tokens
        i = 0
        while i < len(add_tokens):
            token = add_tokens[i]
            if token in self.ARG_FLAGS_WITH_VALUE:
                value = add_tokens[i + 1] if i + 1 < len(add_tokens) else ""
                _remove_flag_instances(token, tokens)
                tokens.append(token)
                tokens.append(value)
                i += 2
                continue
            if token not in tokens:
                tokens.append(token)
            i += 1

        new_string = self._join_tokens(tokens)
        if preview:
            return new_string
        self.extra_args_var.set(new_string)
        return new_string

    def _apply_avoid_dash(self):
        before = (self.extra_args_var.get() or "").strip()
        new_string = self._apply_extra_args_delta(self.AVOID_DASH_TOKENS, preview=True)
        if new_string == before:
            messagebox.showinfo("Evitar DASH", "Los parámetros ya están aplicados en Args extra.")
            return
        self._apply_extra_args_delta(self.AVOID_DASH_TOKENS)
        self._log_line("[*] Añadidos parámetros para evitar segmentos DASH.\n")

    def _consider_make_default(self, attempts, variant_idx):
        if variant_idx is None or variant_idx <= 0:
            return
        try:
            variant = attempts[variant_idx]
        except (IndexError, TypeError):
            return
        add_tokens = variant.get("delta_add", [])
        remove_tokens = variant.get("delta_remove", [])
        if not add_tokens and not remove_tokens:
            return
        current = (self.extra_args_var.get() or "").strip()
        updated = self._apply_extra_args_delta(add_tokens, remove_tokens, preview=True)
        if updated == current:
            return
        if not messagebox.askyesno(
            "Hacer predeterminada",
            "Esta descarga usó una variante avanzada.\n¿Quieres copiar estos parámetros a Args extra?"
        ):
            return
        self._apply_extra_args_delta(add_tokens, remove_tokens)
        self.cfg["extra_args"] = self.extra_args_var.get().strip()
        save_config(self.cfg)
        self._log_line("[*] Variante fijada como predeterminada en Args extra.\n")

    def _save_options(self):
        try:
            q = str(int(self.quality_var.get()))
            if not (0 <= int(q) <= 9):
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "Calidad debe ser un entero 0–9.")
            return
        self.cfg["download_dir"]   = self.dest_var.get().strip()
        self.cfg["audio_quality"]  = q
        self.cfg["audio_format"]   = self.format_var.get().strip()
        self.cfg["extra_args"]     = self.extra_args_var.get().strip()
        if not self._validate_template():
            return
        self.cfg["browser_cookies"]= self.browser_var.get().strip()
        self.cfg["cookies_file"] = self.cookies_file_var.get().strip()
        self.cfg["output_template"] = self.template_var.get().strip()
        self.cfg["playlist"] = self.playlist_var.get()
        save_config(self.cfg)
        self._log_line("[*] Opciones guardadas.\n")

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.dest_var.get())
        if d:
            self.dest_var.set(d)

    def _choose_cookies_file(self):
        current = self.cookies_file_var.get().strip()
        initial_dir = ""
        if current:
            if os.path.isdir(current):
                initial_dir = current
            else:
                initial_dir = os.path.dirname(current)

        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = self.dest_var.get().strip() or os.path.expanduser("~")

        path = filedialog.askopenfilename(
            title="Seleccionar cookies.txt",
            initialdir=initial_dir,
            filetypes=[("cookies.txt", "*.txt"), ("Todos los archivos", "*.*")]
        )

        if path:
            if not os.path.isfile(path):
                messagebox.showerror(
                    "Archivo no encontrado",
                    f"No existe el archivo seleccionado:\n{path}"
                )
                return

            self.cookies_file_var.set(path)

            if getattr(self, "cookies_entry", None):
                try:
                    self.cookies_entry.event_generate("<FocusOut>")
                except Exception:
                    pass


    def _build_cmd_template(self):
        fmt = (self.format_var.get().strip() or "mp3")
        q   = (self.quality_var.get().strip() or "0")
        template = (
            self.template_var.get().strip()
            or "%(title)s.%(ext)s"
        )

        cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", fmt,
            "--audio-quality", q,
            "--embed-thumbnail",
            "--embed-metadata",
            "-o", template
        ]

        # ----------------------------
        # Cookies
        # ----------------------------
        browser = (self.browser_var.get().strip().lower() or "none")
        cookies_file = (
            getattr(self, "cookies_file_var", None)
            and self.cookies_file_var.get().strip()
        )

        if cookies_file:
            cmd.extend(["--cookies", cookies_file])
            self._log_line("[*] Usando cookies desde archivo.\n")

        elif browser != "none":
            cmd.extend(["--cookies-from-browser", browser])
            self._log_line(
                f"[*] Usando cookies desde navegador: {browser}\n"
            )

        # ----------------------------
        # Cliente Android por defecto
        # ----------------------------
        user_args = (
            self.extra_args_var.get().strip()
            if hasattr(self, "extra_args_var")
            else ""
        )

        if "--extractor-args" not in user_args:
            cmd.extend([
                "--extractor-args",
                "youtube:player_client=android"
            ])

        # ----------------------------
        # Args extra del usuario
        # ----------------------------
        if user_args:
            cmd.extend(shlex.split(user_args))

        return cmd


    def _update_queue_status(self, index, prefix):
        try:
            current = self.listbox.get(index)

            if current.startswith("["):
                current = current.split(" ", 1)[1]

            self.listbox.delete(index)
            self.listbox.insert(index, f"{prefix} {current}")

        except Exception:
            pass



    def _apply_preset(self):
        if (self.browser_var.get() or "none").lower() == "none":
            self.browser_var.set("firefox")
        pieces = [
            "--retries", "infinite",
            "--fragment-retries", "infinite",
            "--concurrent-fragments", "1",
            "-4",
            "--user-agent", "Mozilla/5.0",
            "--extractor-args", "youtube:player_client=web,ssap=ignore"
        ]
        current = (self.extra_args_var.get() or "").strip()
        new_args = (current + " " + " ".join(pieces)).strip() if current else " ".join(pieces)
        self.extra_args_var.set(new_args)
        self._log_line(f"[*] Preset anti-403 aplicado (cliente web). Cookies: {self.browser_var.get()}.\n")

    def _build_attempts(self, base_cmd):
        attempts = []
        def add_variant(cmd, delta_add=None, delta_remove=None):
            attempts.append({
                "cmd": cmd,
                "delta_add": list(delta_add or []),
                "delta_remove": list(delta_remove or [])
            })

        add_variant(list(base_cmd))

        dash_tokens = ["-f", "bestaudio[protocol!=http_dash_segments]/bestaudio"]
        chunk_tokens = dash_tokens + ["--http-chunk-size", "10M"]
        prefer_tokens = chunk_tokens + ["--hls-prefer-ffmpeg"]
        web_tokens = prefer_tokens + [
            "--extractor-args", "youtube:player_client=web,ssap=ignore",
            "--user-agent", "Mozilla/5.0"
        ]
        aria_tokens = web_tokens + [
            "--external-downloader", "aria2c",
            "--external-downloader-args", "-x2 -k1M"
        ]

        add_variant(list(base_cmd) + dash_tokens, dash_tokens)
        add_variant(list(base_cmd) + chunk_tokens, chunk_tokens)
        add_variant(list(base_cmd) + prefer_tokens, prefer_tokens)
        add_variant(list(base_cmd) + web_tokens, web_tokens)
        if "-4" in base_cmd:
            # eliminar -4 de base_cmd
            v_cmd = [x for x in base_cmd if x != "-4"]
            add_variant(v_cmd + web_tokens, web_tokens, ["-4"])
        if self.aria2_available:
            add_variant(list(base_cmd) + aria_tokens, aria_tokens)
        return attempts

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
        base_cmd = self._build_cmd_template()
        attempts = self._build_attempts(base_cmd)
        self._log_line(f"[DEBUG] Base CMD: {' '.join(base_cmd)}\n")
        for url in list(self.urls):
            self.download_queue.put(url)
            self._set_item_status(url, "pending")
        self.start_btn.configure(state="disabled")
        self.status_var.set("Descargando…")
        self._log_line(f"== Inicio de descargas ({len(self.urls)} en cola) ==\n")

        def next_download():
            if self.active_dl is not None:
                return
            try:
                url = self.download_queue.get_nowait()
            except queue.Empty:
                self.start_btn.configure(state="normal")
                self.status_var.set("Listo.")
                self._log_line("== Todo descargado ==\n", "ok")
                return

            def done_cb(thread_obj, success, variant_idx):
                self.dl_threads.discard(thread_obj)
                self.active_dl = None
                def apply_status():
                    self._set_item_status(url, "ok" if success else "error")
                    if success:
                        self._consider_make_default(attempts, variant_idx)
                self.after(0, apply_status)
                self.after(100, next_download)

            dl = Downloader(url, outdir, attempts, self.log_queue, done_cb)
            self._set_item_status(url, "downloading")
            self.active_dl = dl
            self.dl_threads.add(dl)
            dl.start()

        next_download()

    def _drain_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple):
                    kind, *payload = item
                    if kind == "progress":
                        url, percent = payload
                        if url in self.urls:
                            self.progress[url] = percent
                            if self.item_status.get(url) != "downloading":
                                self._set_item_status(url, "downloading")
                            else:
                                self._refresh_item_display(url)
                    elif kind == "progress_detailed":
                        url, progress_info = payload
                        if url in self.urls:
                            if not hasattr(self, 'progress_details'):
                                self.progress_details = {}
                            self.progress_details[url] = progress_info
                            if progress_info.percent is not None:
                                self.progress[url] = int(progress_info.percent)
                            if self.item_status.get(url) != "downloading":
                                self._set_item_status(url, "downloading")
                            else:
                                self._refresh_item_display(url)
                            if progress_info.item_current is not None:
                                if hasattr(self, 'progress_details') and url in self.progress_details:
                                    existing = self.progress_details[url]
                                    existing.item_current = progress_info.item_current
                                    existing.item_total = progress_info.item_total
                                else:
                                    if not hasattr(self, 'progress_details'):
                                        self.progress_details = {}
                                    self.progress_details[url] = progress_info
                                self._refresh_item_display(url)
                    continue
                line = item
                tag = "error" if line.startswith("[ERROR]") else ("ok" if line.startswith("[OK]") else None)
                self._log_line(line, tag)
        except queue.Empty:
            pass
        self.after(80, self._drain_log_queue)

    def _log_line(self, text, tag=None):
        self.log.insert("end", text, tag)
        self.log.see("end")
        try:
            self._ensure_log_file()
            with self.log_file_path.open("a", encoding="utf-8") as fh:
                fh.write(text)
        except Exception:
            pass

    def destroy(self):
        for t in list(self.dl_threads):
            try:
                t.stop()
            except Exception:
                pass
        super().destroy()

def main():
    if sys.platform != "win32":
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
