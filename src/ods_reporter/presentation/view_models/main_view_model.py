"""ViewModel principal.

No conoce tkinter: valida las entradas, construye la petición y coordina el hilo
de trabajo. La vista lo consulta y refleja su estado. Así la lógica de la interfaz
es testeable sin abrir una ventana.

El flujo tiene dos fases: ``start()`` analiza los archivos y produce un plan
(vista previa); ``generate()`` aplica ese plan —con las decisiones del usuario—
y genera el documento.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ods_reporter.application.use_cases.ods_plan import ODSPlan, PlanOverrides
from ods_reporter.application.use_cases.process_ods import ProcessODSUseCase, ProcessRequest
from ods_reporter.domain.entities.processing_result import ProcessingResult
from ods_reporter.presentation.workers.gui_progress import GuiProgress
from ods_reporter.presentation.workers.processing_worker import ProcessingWorker
from ods_reporter.shared.constants import EXCEL_EXTENSIONS, MONTHS, WORD_EXTENSIONS
from ods_reporter.shared.result import Result

UseCaseFactory = Callable[[GuiProgress], ProcessODSUseCase]
PlanCallback = Callable[[Result[ODSPlan]], None]
DoneCallback = Callable[[Result[ProcessingResult]], None]


@dataclass(slots=True)
class FormInputs:
    """Datos capturados de la interfaz."""

    word_template: str = ""
    excel_files: tuple[str, ...] = field(default_factory=tuple)
    output_dir: str = ""
    month: str = ""


class MainViewModel:
    """Coordina la validación, el análisis, la generación y la cancelación."""

    def __init__(self, use_case_factory: UseCaseFactory) -> None:
        self._factory = use_case_factory
        self.progress = GuiProgress()
        self._worker: ProcessingWorker[ODSPlan] | ProcessingWorker[ProcessingResult] | None = None
        self._use_case: ProcessODSUseCase | None = None
        self._request: ProcessRequest | None = None
        self.is_running = False

    @property
    def months(self) -> tuple[str, ...]:
        return MONTHS

    def validate(self, inputs: FormInputs) -> list[str]:
        """Devuelve la lista de errores de validación (vacía si todo está bien)."""
        errors: list[str] = []

        if not inputs.word_template:
            errors.append("Selecciona la plantilla Word.")
        elif not inputs.word_template.lower().endswith(WORD_EXTENSIONS):
            errors.append("La plantilla debe ser un archivo .docx.")
        elif not Path(inputs.word_template).exists():
            errors.append("La plantilla Word no existe.")

        if not inputs.excel_files:
            errors.append("Selecciona al menos un archivo Excel.")
        else:
            for excel in inputs.excel_files:
                if not excel.lower().endswith(EXCEL_EXTENSIONS):
                    errors.append(f"Archivo Excel no válido: {Path(excel).name}")

        if not inputs.output_dir:
            errors.append("Selecciona la carpeta de salida.")
        elif not Path(inputs.output_dir).is_dir():
            errors.append("La carpeta de salida no existe.")

        if not inputs.month:
            errors.append("Selecciona el mes a procesar.")

        return errors

    def build_request(self, inputs: FormInputs) -> ProcessRequest:
        return ProcessRequest(
            word_template=Path(inputs.word_template),
            excel_files=tuple(Path(p) for p in inputs.excel_files),
            output_dir=Path(inputs.output_dir),
            month=inputs.month,
        )

    def start(self, inputs: FormInputs, on_plan_ready: PlanCallback) -> list[str]:
        """Valida e inicia el ANÁLISIS (fase de plan) en segundo plano.

        Devuelve la lista de errores de validación; si no está vacía, no arranca.
        """
        errors = self.validate(inputs)
        if errors or self.is_running:
            return errors

        self.progress.reset()
        self._request = self.build_request(inputs)
        self._use_case = self._factory(self.progress)
        self.is_running = True

        use_case, request = self._use_case, self._request

        def done(result: Result[ODSPlan]) -> None:
            # El callback se invoca ANTES de bajar la bandera: quien sondea con
            # ``is_running`` no deja de mirar antes de recibir el resultado.
            on_plan_ready(result)
            self.is_running = False

        self._worker = ProcessingWorker(lambda: use_case.plan(request), done)
        self._worker.start()
        return []

    def generate(
        self, plan: ODSPlan, overrides: PlanOverrides, on_done: DoneCallback
    ) -> bool:
        """Aplica el plan confirmado por el usuario y genera el documento.

        Devuelve ``False`` si no hay un análisis previo o ya hay un proceso activo.
        """
        if self.is_running or self._use_case is None or self._request is None:
            return False

        self.progress.reset()
        self.is_running = True
        use_case, request = self._use_case, self._request

        def done(result: Result[ProcessingResult]) -> None:
            on_done(result)
            self.is_running = False

        self._worker = ProcessingWorker(
            lambda: use_case.apply(request, plan, overrides), done
        )
        self._worker.start()
        return True

    def cancel(self) -> None:
        if self.is_running:
            self.progress.request_cancel()
