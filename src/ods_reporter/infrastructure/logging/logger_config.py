"""Configuración centralizada del logging.

Expone una única función `setup_logging()` que configura el logger raíz con:
  - salida por **consola** (para desarrollo y la futura consola de la GUI),
  - salida a **archivo rotativo** en UTF-8 (para revisiones posteriores).

Mantener esto aislado permite que cualquier módulo use `logging.getLogger(__name__)`
sin preocuparse por la configuración global.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ods_reporter.shared.app_paths import logs_dir
from ods_reporter.shared.constants import LOG_FILE_NAME

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Tamaño máximo por archivo de log antes de rotar (2 MB) y número de respaldos.
_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 5


def setup_logging(
    *,
    level: int = logging.INFO,
    log_dir: Path | None = None,
) -> Path:
    """Configura el logger raíz de la aplicación.

    Parameters
    ----------
    level:
        Nivel mínimo de severidad a registrar (por defecto INFO).
    log_dir:
        Carpeta donde se escribe el archivo de log. Si es ``None`` se usa una
        carpeta de datos del usuario (escribible en cualquier SO), nunca el
        directorio de trabajo (que en el .exe puede ser ``system32``).

    Returns
    -------
    Path
        La ruta del archivo de log activo.
    """
    if log_dir is None:
        log_dir = logs_dir()
    else:
        log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / LOG_FILE_NAME

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)

    # Evita duplicar handlers si setup_logging() se llama más de una vez.
    _clear_handlers(root)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    return log_file


def _clear_handlers(logger: logging.Logger) -> None:
    """Cierra y elimina los handlers existentes de un logger."""
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
