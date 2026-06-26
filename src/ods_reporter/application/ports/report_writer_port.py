"""Puerto del escritor de reportes."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ReportWriterPort(Protocol):
    """Contrato para persistir el resumen del procesamiento."""

    def write(self, content: str, path: Path) -> None:
        """Escribe ``content`` en ``path`` (UTF-8)."""
        ...
