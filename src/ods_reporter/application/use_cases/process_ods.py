"""Caso de uso principal: procesar una ODS (reportes de profesionales -> Word).

Los reportes pueden venir en Excel (modo clásico, el numeral manda) o en Word
(modo Word → Word, donde manda el enunciado de la actividad); el lector
enrutado y el remapeador ocultan la diferencia y el resto del flujo es único.

Orquesta todo el flujo, dejando el documento original intacto y reportando
progreso y eventos. Diseñado para ser robusto: un error en un archivo no detiene
el procesamiento de los demás; los errores se acumulan y el proceso continúa.

El flujo está dividido en dos fases, para poder mostrar una **vista previa**:

  1. ``plan()``: valida, abre la plantilla, lee todos los Excel y calcula qué se
     insertaría dónde, SIN escribir nada. Devuelve un ``ODSPlan``.
  2. ``apply()``: copia la plantilla a la salida y ejecuta el plan, aplicando las
     decisiones del usuario sobre el contenido sin ubicación (``PlanOverrides``).

``execute()`` encadena ambas fases sin decisiones manuales (comportamiento
clásico, usado también por las pruebas de extremo a extremo).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from ods_reporter.application.ports.excel_reader_port import ExcelReaderPort
from ods_reporter.application.ports.file_service_port import FileServicePort
from ods_reporter.application.ports.progress_port import EventLevel, ProgressPort
from ods_reporter.application.ports.report_writer_port import ReportWriterPort
from ods_reporter.application.ports.word_processor_port import WordProcessorPort
from ods_reporter.application.services.activity_remapper import ActivityLabelRemapper
from ods_reporter.application.services.ods_validator import OdsCompatibilityValidator
from ods_reporter.application.services.professional_auditor import ProfessionalAuditor
from ods_reporter.application.services.report_builder import ReportBuilder
from ods_reporter.application.services.report_formatter import ReportFormatter
from ods_reporter.application.use_cases.ods_plan import (
    ODSPlan,
    PlanOverrides,
    PlannedActivity,
)
from ods_reporter.domain.entities.processing_result import ProcessingResult
from ods_reporter.domain.entities.professional import Professional
from ods_reporter.domain.exceptions import InvalidInputError, ODSReporterError
from ods_reporter.shared.constants import (
    DEFAULT_EMPTY_ACTIVITY_TEXT,
    PROFESSIONAL_FILE_EXTENSIONS,
    WORD_EXTENSIONS,
)
from ods_reporter.shared.result import Err, Ok, Result

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProcessRequest:
    """Parámetros de una ejecución de procesamiento."""

    word_template: Path
    excel_files: tuple[Path, ...]
    output_dir: Path
    month: str
    output_name: str = ""  # si está vacío, se deriva de la plantilla

    @property
    def resolved_output_name(self) -> str:
        if self.output_name:
            return self.output_name
        stem = self.word_template.stem
        return f"{stem}_{self.month}.docx"


@dataclass
class _Dependencies:
    """Agrupa las dependencias inyectadas en el caso de uso."""

    excel_reader: ExcelReaderPort
    word_processor: WordProcessorPort
    file_service: FileServicePort
    report_writer: ReportWriterPort | None = None
    report_builder: ReportBuilder = field(default_factory=ReportBuilder)
    auditor: ProfessionalAuditor = field(default_factory=ProfessionalAuditor)
    report_formatter: ReportFormatter = field(default_factory=ReportFormatter)
    validator: OdsCompatibilityValidator = field(default_factory=OdsCompatibilityValidator)
    remapper: ActivityLabelRemapper = field(default_factory=ActivityLabelRemapper)


class ProcessODSUseCase:
    """Orquesta el procesamiento completo de una ODS."""

    def __init__(
        self,
        excel_reader: ExcelReaderPort,
        word_processor: WordProcessorPort,
        file_service: FileServicePort,
        progress: ProgressPort,
        *,
        report_writer: ReportWriterPort | None = None,
        report_builder: ReportBuilder | None = None,
        auditor: ProfessionalAuditor | None = None,
    ) -> None:
        self._deps = _Dependencies(
            excel_reader=excel_reader,
            word_processor=word_processor,
            file_service=file_service,
            report_writer=report_writer,
            report_builder=report_builder or ReportBuilder(),
            auditor=auditor or ProfessionalAuditor(),
        )
        self._progress = progress

    # --- Fase 1: análisis (vista previa) ---

    def plan(self, request: ProcessRequest) -> Result[ODSPlan]:
        """Lee y empareja todo sin escribir: el insumo de la vista previa."""
        try:
            self._validate(request)
        except InvalidInputError as exc:
            self._progress.event(EventLevel.ERROR, str(exc))
            return Err(str(exc), exc)

        try:
            self._deps.word_processor.open(request.word_template)
        except ODSReporterError as exc:
            self._progress.event(EventLevel.ERROR, str(exc))
            return Err(str(exc), exc)

        overview = self._deps.word_processor.get_activities_overview()
        self._progress.event(
            EventLevel.INFO,
            f"Plantilla analizada: {len(overview)} actividad(es). "
            f"Analizando {len(request.excel_files)} archivo(s) de profesionales…",
        )

        professionals: list[Professional] = []
        planned: list[PlannedActivity] = []
        read_errors: list[str] = []
        general_warnings: list[str] = []
        cancelled = False
        total = len(request.excel_files)

        word_ods_number = self._deps.word_processor.get_ods_number()

        for index, excel in enumerate(request.excel_files):
            if self._progress.is_cancelled():
                cancelled = True
                break
            if self._is_template_itself(excel, request.word_template):
                message = (
                    f"'{excel.name}' es la misma plantilla Word de destino: se omitió."
                )
                general_warnings.append(message)
                self._progress.event(EventLevel.WARNING, message)
                self._progress.progress(index + 1, total)
                continue
            professional = self._read_professional(excel, request.month, read_errors)
            self._progress.progress(index + 1, total)
            if professional is None:
                continue
            # Barrera anti "ODS equivocada": un archivo incompatible se rechaza
            # (con su motivo) y NO se inserta; los demás continúan.
            check = self._deps.validator.validate(professional, overview, word_ods_number)
            if not check.compatible:
                message = (
                    f"El archivo '{excel.name}' no corresponde a esta ODS: "
                    f"{check.reason}. No se procesó."
                )
                read_errors.append(message)
                self._progress.event(EventLevel.ERROR, message)
                continue
            # Modo Word → Word: el numeral del documento del profesional puede no
            # coincidir con el de la plantilla; manda el ENUNCIADO de la actividad.
            if excel.suffix.lower() in WORD_EXTENSIONS:
                professional, remap_warnings = self._deps.remapper.remap(
                    professional, overview
                )
                origin = self._origin_label(professional)
                for warning in remap_warnings:
                    message = f"{warning} [{origin}]"
                    general_warnings.append(message)
                    self._progress.event(EventLevel.WARNING, message)
            planned.extend(self._plan_professional(len(professionals), professional))
            professionals.append(professional)

        if cancelled:
            self._progress.event(EventLevel.WARNING, "Análisis cancelado por el usuario.")

        other_count = sum(len(p.other_activities) for p in professionals)
        has_other_section = self._deps.word_processor.has_other_activities_section()
        if other_count:
            self._progress.event(
                EventLevel.INFO,
                f"{other_count} actividad(es) adicional(es) detectada(s) "
                "en los archivos.",
            )
            if not has_other_section:
                general_warnings.append(
                    "El Word no tiene la sección de observaciones/actividades "
                    f"adicionales: se omitirán {other_count} ítem(s)."
                )

        return Ok(
            ODSPlan(
                month=request.month,
                word_activities=tuple(overview),
                planned=tuple(planned),
                professionals=tuple(professionals),
                read_errors=tuple(read_errors),
                cancelled=cancelled,
                other_activities_count=other_count,
                word_has_other_section=has_other_section,
                general_warnings=tuple(general_warnings),
            )
        )

    def _plan_professional(
        self, professional_index: int, professional: Professional
    ) -> list[PlannedActivity]:
        origin = self._origin_label(professional)
        planned: list[PlannedActivity] = []
        for activity in professional.activities:
            if not activity.has_content:
                continue
            outcome = self._deps.word_processor.plan_activity_content(
                activity, professional_name=professional.name
            )
            items = (
                outcome.items_written
                if outcome.matched
                else len(activity.all_content_items)
            )
            planned.append(
                PlannedActivity(
                    professional_index=professional_index,
                    professional_name=professional.name or "profesional desconocido",
                    source_file=professional.source_file,
                    ordinal=activity.ordinal,
                    label=activity.label,
                    items_count=items,
                    matched=outcome.matched,
                    warnings=tuple(f"{w} [{origin}]" for w in outcome.warnings),
                )
            )
        return planned

    # --- Fase 2: aplicación del plan ---

    def apply(
        self,
        request: ProcessRequest,
        plan: ODSPlan,
        overrides: PlanOverrides | None = None,
        *,
        started_at: float | None = None,
    ) -> Result[ProcessingResult]:
        """Genera el documento ejecutando ``plan`` con las decisiones del usuario."""
        start = started_at if started_at is not None else time.monotonic()
        overrides = overrides or {}
        result = ProcessingResult()
        for error in plan.read_errors:
            result.add_error(error)

        output_file = request.output_dir / request.resolved_output_name
        try:
            self._deps.file_service.copy(request.word_template, output_file)
            self._deps.word_processor.open(output_file)
        except ODSReporterError as exc:
            self._progress.event(EventLevel.ERROR, str(exc))
            return Err(str(exc), exc)

        self._progress.event(
            EventLevel.INFO,
            f"Plantilla copiada y abierta. Generando con "
            f"{len(plan.professionals)} profesional(es).",
        )

        total = len(plan.professionals)
        for index, professional in enumerate(plan.professionals):
            if self._progress.is_cancelled():
                result.cancelled = True
                break
            result.professionals_processed += 1
            self._insert_professional_content(
                professional, result, professional_index=index, overrides=overrides
            )
            self._progress.progress(index + 1, total)

        if result.cancelled:
            result.elapsed_seconds = time.monotonic() - start
            self._progress.event(EventLevel.WARNING, "Proceso cancelado por el usuario.")
            return Ok(result)

        self._insert_other_activities(plan, result)
        self._finalize(request, result, list(plan.professionals), output_file)
        result.elapsed_seconds = time.monotonic() - start
        self._write_report(request, result, output_file)
        self._progress.event(
            EventLevel.SUCCESS,
            f"Proceso completado en {result.elapsed_seconds:.1f}s. Salida: {output_file.name}",
        )
        return Ok(result)

    # --- Flujo completo sin vista previa ---

    def execute(self, request: ProcessRequest) -> Result[ProcessingResult]:
        """Plan + aplicación sin decisiones manuales (flujo clásico)."""
        start = time.monotonic()
        plan_result = self.plan(request)
        if plan_result.is_err():
            return Err(plan_result.error or "Error al analizar los archivos.")
        plan = plan_result.unwrap()

        if plan.cancelled:
            result = ProcessingResult(cancelled=True)
            for error in plan.read_errors:
                result.add_error(error)
            result.elapsed_seconds = time.monotonic() - start
            return Ok(result)

        return self.apply(request, plan, {}, started_at=start)

    # --- Validación ---

    def _validate(self, request: ProcessRequest) -> None:
        if not request.word_template.exists():
            raise InvalidInputError(f"No existe la plantilla Word: {request.word_template}")
        if request.word_template.suffix.lower() not in WORD_EXTENSIONS:
            raise InvalidInputError("La plantilla debe ser un archivo .docx")
        if not request.excel_files:
            raise InvalidInputError("No se seleccionó ningún archivo de profesionales.")
        for excel in request.excel_files:
            if excel.suffix.lower() not in PROFESSIONAL_FILE_EXTENSIONS:
                raise InvalidInputError(
                    f"Archivo de profesional no válido: {excel.name} "
                    "(se admiten Excel .xlsx/.xlsm y Word .docx)."
                )
        if not request.month.strip():
            raise InvalidInputError("Debe indicarse el mes a procesar.")

    @staticmethod
    def _is_template_itself(candidate: Path, template: Path) -> bool:
        """``True`` si el archivo de profesional ES la plantilla de destino.

        Evita que, al agregar una carpeta completa, la propia plantilla entre
        como si fuera el reporte de un profesional.
        """
        try:
            return candidate.resolve() == template.resolve()
        except OSError:
            return False

    # --- Lectura por profesional ---

    def _read_professional(
        self, excel: Path, month: str, errors: list[str]
    ) -> Professional | None:
        try:
            raw = self._deps.excel_reader.read_month(excel, month)
            professional = self._deps.report_builder.build(raw)
        except ODSReporterError as exc:
            message = f"Error al leer '{excel.name}': {exc}"
            errors.append(message)
            self._progress.event(EventLevel.ERROR, message)
            return None
        except Exception as exc:  # noqa: BLE001 - robustez: un archivo no detiene el resto
            logger.exception("Error inesperado leyendo %s", excel.name)
            message = f"Error inesperado en '{excel.name}': {exc}"
            errors.append(message)
            self._progress.event(EventLevel.ERROR, message)
            return None

        self._progress.event(
            EventLevel.INFO,
            f"Leído '{excel.name}' ({professional.name or 'profesional desconocido'}): "
            f"{professional.content_activity_count} actividad(es) con contenido.",
        )
        return professional

    # --- Inserción ---

    def _insert_professional_content(
        self,
        professional: Professional,
        result: ProcessingResult,
        *,
        professional_index: int = 0,
        overrides: PlanOverrides | None = None,
    ) -> None:
        overrides = overrides or {}
        # Origen mostrado en errores/advertencias para poder revisar el archivo culpable.
        origin = self._origin_label(professional)
        for activity in professional.activities:
            if not activity.has_content:
                continue

            target: int | None = None
            key = (professional_index, activity.ordinal)
            if key in overrides:
                target = overrides[key]
                if target is None:
                    message = (
                        f"Actividad {activity.ordinal} omitida por el usuario [{origin}]."
                    )
                    result.add_warning(message)
                    self._progress.event(EventLevel.WARNING, message)
                    continue

            try:
                insert = self._deps.word_processor.insert_activity_content(
                    activity, target_ordinal=target, professional_name=professional.name
                )
            except Exception as exc:  # noqa: BLE001 - una actividad no detiene el resto
                logger.exception(
                    "Error insertando actividad %s de %s", activity.ordinal, origin
                )
                message = (
                    f"Error al insertar la actividad {activity.ordinal} "
                    f"[{origin}]: {exc}"
                )
                result.add_error(message)
                self._progress.event(EventLevel.ERROR, message)
                continue

            if not insert.matched:
                result.activities_not_found += 1
            else:
                result.activities_with_content += 1
                result.items_written += insert.items_written
            result.entregables_unmatched += insert.entregables_unmatched
            for warning in insert.warnings:
                full_warning = f"{warning} [{origin}]"
                result.add_warning(full_warning)
                self._progress.event(EventLevel.WARNING, full_warning)

    def _insert_other_activities(self, plan: ODSPlan, result: ProcessingResult) -> None:
        """Inserta las actividades adicionales de todos los profesionales."""
        items = tuple(
            item
            for professional in plan.professionals
            for item in professional.other_activities
        )
        if not items:
            return
        if not self._deps.word_processor.has_other_activities_section():
            message = (
                "El Word no tiene la sección de observaciones/actividades "
                f"adicionales: se omitieron {len(items)} ítem(s)."
            )
            result.add_warning(message)
            self._progress.event(EventLevel.WARNING, message)
            return
        written = self._deps.word_processor.insert_other_activities(items)
        result.other_activities_written = written
        self._progress.event(
            EventLevel.INFO,
            f"Insertada(s) {written} actividad(es) adicional(es) en Observaciones.",
        )

    @staticmethod
    def _origin_label(professional: Professional) -> str:
        """Etiqueta de origen 'Profesional (archivo.xlsx)' para los mensajes."""
        name = professional.name or "profesional desconocido"
        if professional.source_file:
            return f"{name} – {professional.source_file}"
        return name

    # --- Cierre ---

    def _finalize(
        self,
        request: ProcessRequest,
        result: ProcessingResult,
        professionals: list[Professional],
        output_file: Path,
    ) -> None:
        result.default_slots_filled = self._deps.word_processor.fill_empty_with_default(
            DEFAULT_EMPTY_ACTIVITY_TEXT
        )
        result.audit = self._deps.auditor.audit(professionals)
        self._deps.word_processor.save(output_file)
        result.output_path = str(output_file)

    def _write_report(
        self, request: ProcessRequest, result: ProcessingResult, output_file: Path
    ) -> None:
        """Genera el resumen y, si hay escritor, lo guarda junto a la salida."""
        result.summary = self._deps.report_formatter.format(result, month=request.month)
        if self._deps.report_writer is None:
            return
        report_path = output_file.with_name(f"{output_file.stem}_reporte.txt")
        self._deps.report_writer.write(result.summary, report_path)
