"""Adaptador de progreso que comunica el caso de uso con la interfaz.

Implementa ``ProgressPort``. Como tkinter no es seguro entre hilos, el hilo de
trabajo no toca los widgets: publica mensajes en una cola y la interfaz los
consume desde el hilo principal. La cancelación se señaliza con un ``Event``.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass

from ods_reporter.application.ports.progress_port import EventLevel


@dataclass(frozen=True, slots=True)
class EventMessage:
    """Mensaje de evento para la consola de la interfaz."""

    level: EventLevel
    text: str


@dataclass(frozen=True, slots=True)
class ProgressMessage:
    """Mensaje de avance numérico para la barra de progreso."""

    current: int
    total: int


class GuiProgress:
    """Puente entre el caso de uso (hilo de trabajo) y la interfaz (hilo principal)."""

    def __init__(self) -> None:
        self.queue: queue.Queue[EventMessage | ProgressMessage] = queue.Queue()
        self._cancel = threading.Event()

    # --- ProgressPort ---

    def event(self, level: EventLevel, message: str) -> None:
        self.queue.put(EventMessage(level=level, text=message))

    def progress(self, current: int, total: int) -> None:
        self.queue.put(ProgressMessage(current=current, total=total))

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    # --- Control desde la interfaz ---

    def request_cancel(self) -> None:
        self._cancel.set()

    def reset(self) -> None:
        self._cancel.clear()
        while not self.queue.empty():
            self.queue.get_nowait()
