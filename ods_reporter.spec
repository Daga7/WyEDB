# -*- mode: python ; coding: utf-8 -*-
"""Configuración de PyInstaller para ODS Reporter.

Genera un único ejecutable (onefile) sin ventana de consola. Funciona en el SO
donde se ejecute: en Windows produce 'ODS Reporter.exe', en Linux un binario.

Uso:
    pyinstaller ods_reporter.spec
"""

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# CustomTkinter incluye temas/imágenes que deben empaquetarse como datos.
datas = collect_data_files("customtkinter")
hiddenimports = collect_submodules("customtkinter")

# Imágenes de marca S.G.I. (logo de cabecera e iconos de ventana).
datas += [
    ("assets/logo.png", "assets"),
    ("assets/icon.png", "assets"),
    ("assets/icon.ico", "assets"),
]
# Ilustraciones decorativas opcionales (barra lateral y carril derecho).
for _decoration in ("assets/side_left.png", "assets/side_right.png"):
    if os.path.exists(_decoration):
        datas.append((_decoration, "assets"))

# Icono y metadatos de versión (Windows). Opcionales: si el archivo no existe,
# se omiten sin romper la compilación en otros sistemas.
_icon = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None
_version_file = (
    "packaging/version_info.txt" if os.path.exists("packaging/version_info.txt") else None
)

block_cipher = None

a = Analysis(
    ["src/ods_reporter/main.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "mypy", "ruff"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ODS Reporter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX desactivado: la compresión dispara falsos positivos de antivirus.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # sin ventana de consola (aplicación de escritorio)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
    version=_version_file,
)
