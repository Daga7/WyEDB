"""Hilo de trabajo que ejecuta el caso de uso sin congelar la interfaz."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from ods_reporter.application.use_cases.process_ods import ProcessODSUseCase, ProcessRequest
from ods_reporter.domain.entities.processing_result import ProcessingResult
from ods_reporter.shared.result import Err, Result

logger = logging.getLogger(__name__)

DoneCallback = Callable[[Result[ProcessingResult]], None]


class ProcessingWorker(threading.Thread):
    """Ejecuta ``ProcessODSUseCase`` en segundo plano y avisa al terminar."""

    def __init__(
        self,
        use_case: ProcessODSUseCase,
        request: ProcessRequest,
        on_done: DoneCallback,
    ) -> None:
        super().__init__(daemon=True)
        self._use_case = use_case
        self._request = request
        self._on_done = on_done

    def run(self) -> None:
        try:
            result = self._use_case.execute(self._request)
        except Exception as exc:  # red de seguridad: nunca debe propagar al hilo
            logger.exception("Error inesperado en el procesamiento")
            result = Err(f"Error inesperado: {exc}", exc)
        self._on_done(result)
