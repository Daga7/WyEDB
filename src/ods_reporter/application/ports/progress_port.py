"""Puerto de notificación de progreso.

Permite que el caso de uso informe avance y eventos sin conocer la interfaz
(consola, GUI, log...). La presentación implementa este contrato para reflejar el
estado en tiempo real; las pruebas usan una implementación simple en memoria.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol


class EventLevel(Enum):
    """Severidad de un evento informado al usuario."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class ProgressPort(Protocol):
    """Contrato para informar progreso y eventos del procesamiento."""

    def event(self, level: EventLevel, message: str) -> None:
        """Informa un evento (mensaje para la consola/log)."""
        ...

    def progress(self, current: int, total: int) -> None:
        """Informa el avance numérico (para la barra de progreso)."""
        ...

    def is_cancelled(self) -> bool:
        """``True`` si el usuario solicitó cancelar el proceso."""
        ...
