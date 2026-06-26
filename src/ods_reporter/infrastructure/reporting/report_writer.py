"""Escritor de reportes a archivo de texto (UTF-8)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ReportWriter:
    """Persiste el resumen del procesamiento (implementa ``ReportWriterPort``)."""

    def write(self, content: str, path: Path) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            logger.info("Reporte guardado en: %s", path)
        except OSError as exc:
            # El reporte es secundario: si falla, se registra pero no se interrumpe.
            logger.warning("No se pudo guardar el reporte en %s: %s", path, exc)
