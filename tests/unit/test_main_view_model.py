"""Pruebas del ViewModel y el puente de progreso (sin interfaz gráfica)."""

from __future__ import annotations

import time
from pathlib import Path

from ods_reporter.application.ports.progress_port import EventLevel
from ods_reporter.application.use_cases.ods_plan import ODSPlan
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

def _empty_plan(month: str = "MAYO") -> ODSPlan:
    return ODSPlan(
        month=month,
        word_activities=(),
        planned=(),
        professionals=(),
    )


class _FakeUseCase:
    def __init__(self, progress) -> None:  # type: ignore[no-untyped-def]
        self._progress = progress

    def plan(self, request) -> Result[ODSPlan]:  # type: ignore[no-untyped-def]
        self._progress.event(EventLevel.INFO, "analizando")
        self._progress.progress(1, 1)
        return Ok(_empty_plan(request.month))

    def apply(self, request, plan, overrides=None):  # type: ignore[no-untyped-def]
        self._progress.event(EventLevel.INFO, "generando")
        return Ok(ProcessingResult(professionals_processed=1))


def _wait_until_idle(vm: MainViewModel) -> None:
    deadline = time.time() + 5
    while vm.is_running and time.time() < deadline:
        time.sleep(0.01)


def test_start_runs_worker_and_delivers_plan(tmp_path: Path) -> None:
    vm = MainViewModel(use_case_factory=_FakeUseCase)  # type: ignore[arg-type]
    received: list[Result[ODSPlan]] = []

    errors = vm.start(_valid_inputs(tmp_path), on_plan_ready=received.append)
    assert errors == []
    _wait_until_idle(vm)

    assert vm.is_running is False
    assert len(received) == 1
    assert received[0].is_ok()
    assert received[0].unwrap().month == "MAYO"
    # Los eventos quedaron en la cola para que la vista los consuma.
    assert not vm.progress.queue.empty()


def test_generate_after_plan_calls_done(tmp_path: Path) -> None:
    vm = MainViewModel(use_case_factory=_FakeUseCase)  # type: ignore[arg-type]
    plans: list[Result[ODSPlan]] = []
    vm.start(_valid_inputs(tmp_path), on_plan_ready=plans.append)
    _wait_until_idle(vm)

    done: list[Result[ProcessingResult]] = []
    assert vm.generate(plans[0].unwrap(), {}, on_done=done.append) is True
    _wait_until_idle(vm)

    assert len(done) == 1
    assert done[0].is_ok()
    assert done[0].unwrap().professionals_processed == 1


def test_generate_without_previous_plan_is_rejected() -> None:
    vm = MainViewModel(use_case_factory=_FakeUseCase)  # type: ignore[arg-type]
    assert vm.generate(_empty_plan(), {}, on_done=lambda r: None) is False


def test_start_blocked_by_validation_errors() -> None:
    vm = MainViewModel(use_case_factory=_FakeUseCase)  # type: ignore[arg-type]
    errors = vm.start(FormInputs(), on_plan_ready=lambda r: None)
    assert errors
    assert vm.is_running is False
