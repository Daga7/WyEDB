"""Pruebas del ViewModel y el puente de progreso (sin interfaz gráfica)."""

from __future__ import annotations

import time
from pathlib import Path

from ods_reporter.application.ports.progress_port import EventLevel
from ods_reporter.domain.entities.processing_result import ProcessingResult
from ods_reporter.presentation.view_models.main_view_model import FormInputs, MainViewModel
from ods_reporter.presentation.workers.gui_progress import (
    EventMessage,
    GuiProgress,
    ProgressMessage,
)
from ods_reporter.shared.result import Ok, Result


# --- GuiProgress ---

def test_gui_progress_queues_events_and_progress() -> None:
    progress = GuiProgress()
    progress.event(EventLevel.INFO, "hola")
    progress.progress(2, 5)
    first = progress.queue.get_nowait()
    second = progress.queue.get_nowait()
    assert isinstance(first, EventMessage)
    assert first.text == "hola"
    assert isinstance(second, ProgressMessage)
    assert (second.current, second.total) == (2, 5)


def test_gui_progress_cancellation() -> None:
    progress = GuiProgress()
    assert progress.is_cancelled() is False
    progress.request_cancel()
    assert progress.is_cancelled() is True
    progress.reset()
    assert progress.is_cancelled() is False


# --- ViewModel: validación ---

def _valid_inputs(tmp_path: Path) -> FormInputs:
    word = tmp_path / "plantilla.docx"
    word.write_text("x")
    excel = tmp_path / "datos.xlsx"
    excel.write_text("x")
    return FormInputs(
        word_template=str(word),
        excel_files=(str(excel),),
        output_dir=str(tmp_path),
        month="MAYO",
    )


def test_validate_passes_with_valid_inputs(tmp_path: Path) -> None:
    vm = MainViewModel(use_case_factory=lambda p: None)  # type: ignore[arg-type,return-value]
    assert vm.validate(_valid_inputs(tmp_path)) == []


def test_validate_reports_missing_fields() -> None:
    vm = MainViewModel(use_case_factory=lambda p: None)  # type: ignore[arg-type,return-value]
    errors = vm.validate(FormInputs())
    assert any("plantilla" in e.lower() for e in errors)
    assert any("excel" in e.lower() for e in errors)
    assert any("salida" in e.lower() for e in errors)
    assert any("mes" in e.lower() for e in errors)


def test_validate_rejects_wrong_extensions(tmp_path: Path) -> None:
    word = tmp_path / "archivo.txt"
    word.write_text("x")
    vm = MainViewModel(use_case_factory=lambda p: None)  # type: ignore[arg-type,return-value]
    errors = vm.validate(
        FormInputs(
            word_template=str(word),
            excel_files=(str(word),),
            output_dir=str(tmp_path),
            month="MAYO",
        )
    )
    assert any(".docx" in e for e in errors)


# --- ViewModel: arranque con caso de uso falso ---

class _FakeUseCase:
    def __init__(self, progress) -> None:  # type: ignore[no-untyped-def]
        self._progress = progress

    def execute(self, request) -> Result[ProcessingResult]:  # type: ignore[no-untyped-def]
        self._progress.event(EventLevel.INFO, "procesando")
        self._progress.progress(1, 1)
        return Ok(ProcessingResult(professionals_processed=1))


def test_start_runs_worker_and_calls_done(tmp_path: Path) -> None:
    vm = MainViewModel(use_case_factory=_FakeUseCase)  # type: ignore[arg-type]
    received: list[Result[ProcessingResult]] = []

    errors = vm.start(_valid_inputs(tmp_path), on_done=received.append)
    assert errors == []

    # Esperar a que el worker termine.
    deadline = time.time() + 5
    while vm.is_running and time.time() < deadline:
        time.sleep(0.01)

    assert vm.is_running is False
    assert len(received) == 1
    assert received[0].is_ok()
    assert received[0].unwrap().professionals_processed == 1
    # Los eventos quedaron en la cola para que la vista los consuma.
    assert not vm.progress.queue.empty()


def test_start_blocked_by_validation_errors() -> None:
    vm = MainViewModel(use_case_factory=_FakeUseCase)  # type: ignore[arg-type]
    errors = vm.start(FormInputs(), on_done=lambda r: None)
    assert errors
    assert vm.is_running is False
