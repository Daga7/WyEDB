"""Abrir archivos o carpetas en el explorador del sistema (multiplataforma)."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def open_path(path: Path | str) -> bool:
    """Abre ``path`` (archivo o carpeta) con la aplicación predeterminada del SO.

    Devuelve ``True`` si se lanzó el comando, ``False`` si hubo un problema.
    """
    target = str(path)
    try:
        if sys.platform.startswith("win"):
            import os

            os.startfile(target)  # type: ignore[attr-defined]  # solo Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return True
    except Exception as exc:  # noqa: BLE001 - abrir es secundario, no debe romper
        logger.warning("No se pudo abrir '%s': %s", target, exc)
        return False
