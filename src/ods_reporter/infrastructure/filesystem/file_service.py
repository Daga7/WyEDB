"""Implementación del servicio de archivos basada en ``shutil``."""

from __future__ import annotations

import shutil
from pathlib import Path

from ods_reporter.domain.exceptions import InvalidInputError


class FileService:
    """Operaciones de archivos (implementa ``FileServicePort``)."""

    def copy(self, source: Path, destination: Path) -> None:
        if not source.exists():
            raise InvalidInputError(f"No existe el archivo origen: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        # copy2 conserva metadatos; el contenido del .docx queda intacto.
        shutil.copy2(source, destination)
