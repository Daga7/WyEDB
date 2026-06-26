"""Rutas de datos de la aplicación, válidas en cualquier sistema operativo.

Evita escribir en el directorio de trabajo (que al ejecutar el .exe puede ser
``C:\\Windows\\system32``, sin permisos). Usa una carpeta del **usuario**:

  - Windows: ``%LOCALAPPDATA%\\ODS Reporter``
  - macOS:   ``~/Library/Application Support/ODS Reporter``
  - Linux:   ``~/.local/share/ODS Reporter`` (o ``$XDG_DATA_HOME``)

Si por algún motivo no se puede crear, recurre a una carpeta temporal.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from ods_reporter.shared.constants import APP_NAME, LOG_DIR_NAME


def user_data_dir() -> Path:
    """Carpeta de datos de la aplicación para el usuario actual."""
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME")
        root = Path(base) if base else Path.home() / ".local" / "share"
    return root / APP_NAME


def logs_dir() -> Path:
    """Carpeta donde escribir los logs; garantiza que exista y sea escribible."""
    candidate = user_data_dir() / LOG_DIR_NAME
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except OSError:
        # Último recurso: carpeta temporal del sistema (siempre escribible).
        fallback = Path(tempfile.gettempdir()) / APP_NAME / LOG_DIR_NAME
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
