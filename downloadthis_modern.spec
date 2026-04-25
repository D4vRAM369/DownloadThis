# -*- mode: python ; coding: utf-8 -*-
import os, sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

dnd_datas    = collect_data_files("tkinterdnd2")
dnd_binaries = collect_dynamic_libs("tkinterdnd2")

a = Analysis(
    ["downloadthis_modern.py"],
    pathex=[],
    binaries=dnd_binaries,
    datas=dnd_datas,
    hiddenimports=[
        "tkinterdnd2",
        "ttkbootstrap",
        "ttkbootstrap.themes",
        "yt_dlp",
        "yt_dlp.extractor",
        "yt_dlp.downloader",
        "yt_dlp.postprocessor",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "pandas", "PIL", "cv2"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="downloadthis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join("packaging", "icon.ico") if sys.platform == "win32"
         else os.path.join("packaging", "icon.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="downloadthis",
)
