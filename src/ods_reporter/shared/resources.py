"""Localización de recursos de la aplicación (imágenes de marca).

Con PyInstaller (onefile) los datos empaquetados se extraen a ``sys._MEIPASS``;
en desarrollo, los recursos viven en la carpeta ``assets/`` de la raíz del
repositorio. Esta función resuelve ambos casos.
"""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Ruta absoluta a un recurso empaquetado o del repositorio.

    ``relative`` se expresa desde la raíz (p. ej. ``"assets/logo.png"``).
    """
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir) / relative
    return Path(__file__).resolve().parents[3] / relative
