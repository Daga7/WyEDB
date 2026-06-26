"""Puerto del servicio de archivos (copiar plantilla, validar rutas)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class FileServicePort(Protocol):
    """Contrato para operaciones de archivos que necesita el caso de uso."""

    def copy(self, source: Path, destination: Path) -> None:
        """Copia ``source`` a ``destination`` (creando carpetas si hace falta)."""
        ...
