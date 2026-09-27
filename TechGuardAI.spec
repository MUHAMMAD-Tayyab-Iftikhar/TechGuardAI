# -*- mode: python ; coding: utf-8 -*-
# TechGuardAI — PyInstaller Build Specification
# Run `build.bat` to produce the distributable in dist/TechGuardAI/

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Collect CustomTkinter's theme/image assets ────────────────────────────────
ctk_datas = collect_data_files("customtkinter", include_py_files=False)

# ── Hidden imports (modules PyInstaller can't detect automatically) ───────────
hidden = [
    # Google GenAI SDK
    "google.genai",
    "google.api_core",
    "google.api_core.exceptions",
    "google.auth",
    "google.auth.transport.requests",
    # Windows-specific
    "wmi",
    "win32api",
    "win32con",
    "win32security",
    "win32evtlog",
    "pywintypes",
    "win32com.client",
    # Standard lib / other
    "configparser",
    "sqlite3",
    "tkinter",
    "tkinter.simpledialog",
    "tkinter.messagebox",
    "PIL._tkinter_finder",
    "screeninfo",
    "psutil",
    # Firebase / Pyrebase4
    "pyrebase",
    "requests",
    "requests.adapters",
    "requests.auth",
    "requests.packages",
    "urllib3",
    "certifi",
    "jwt",
    "python_jwt",
    "gcloud",
    "oauth2client",
    # Auth package
    "auth",
    "auth.firebase_auth",
]
hidden += collect_submodules("google.genai")
hidden += collect_submodules("google.api_core")
hidden += collect_submodules("pyrebase")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=ctk_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "unittest", "test"],
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
    name="TechGuardAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # No black console window — GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,            # Add icon="icon.ico" here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TechGuardAI",  # Output folder: dist/TechGuardAI/
)
