"""Hilo de trabajo que ejecuta una tarea del caso de uso sin congelar la interfaz.

Es genérico: recibe una función sin argumentos que devuelve un ``Result`` (la
fase de análisis o la de generación) y avisa al terminar por el callback.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Generic, TypeVar

from ods_reporter.shared.result import Err, Result

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ProcessingWorker(threading.Thread, Generic[T]):
    """Ejecuta una tarea en segundo plano y avisa al terminar."""

    def __init__(
        self,
        task: Callable[[], Result[T]],
        on_done: Callable[[Result[T]], None],
    ) -> None:
        super().__init__(daemon=True)
        self._task = task
        self._on_done = on_done

    def run(self) -> None:
        try:
            result = self._task()
        except Exception as exc:  # red de seguridad: nunca debe propagar al hilo
            logger.exception("Error inesperado en el procesamiento")
            result = Err(f"Error inesperado: {exc}", exc)
        self._on_done(result)
