"""Caso de uso principal: procesar una ODS (Excel(es) -> Word).

Orquesta todo el flujo, dejando el documento original intacto y reportando
progreso y eventos. Diseñado para ser robusto: un error en un Excel no detiene el
procesamiento de los demás; los errores se acumulan y el proceso continúa.

Flujo:
    1. Validar entradas.
    2. Copiar la plantilla Word a la carpeta de salida.
    3. Abrir el Word de salida.
    4. Por cada Excel (profesional): leer el mes, construir el dominio, insertar
       el contenido de sus actividades (emparejando por numeral, alineando
       entregables por texto).
    5. Rellenar con el texto por defecto los slots que quedaron vacíos.
    6. Auditar profesionales (sin actividades / por debajo del umbral).
    7. Guardar el documento.
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
from ods_reporter.application.services.professional_auditor import ProfessionalAuditor
from ods_reporter.application.services.report_builder import ReportBuilder
from ods_reporter.application.services.report_formatter import ReportFormatter
from ods_reporter.domain.entities.processing_result import ProcessingResult
from ods_reporter.domain.entities.professional import Professional
from ods_reporter.domain.exceptions import InvalidInputError, ODSReporterError
from ods_reporter.shared.constants import (
    DEFAULT_EMPTY_ACTIVITY_TEXT,
    EXCEL_EXTENSIONS,
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

    def execute(self, request: ProcessRequest) -> Result[ProcessingResult]:
        start = time.monotonic()
        result = ProcessingResult()

        try:
            self._validate(request)
        except InvalidInputError as exc:
            self._progress.event(EventLevel.ERROR, str(exc))
            return Err(str(exc), exc)

        output_file = request.output_dir / request.resolved_output_name
        try:
            self._deps.file_service.copy(request.word_template, output_file)
            self._deps.word_processor.open(output_file)
        except ODSReporterError as exc:
            self._progress.event(EventLevel.ERROR, str(exc))
            return Err(str(exc), exc)

        self._progress.event(
            EventLevel.INFO,
            f"Plantilla copiada y abierta. Procesando {len(request.excel_files)} archivo(s).",
        )

        professionals = self._process_professionals(request, result)

        if self._progress.is_cancelled():
            result.cancelled = True
            result.elapsed_seconds = time.monotonic() - start
            self._progress.event(EventLevel.WARNING, "Proceso cancelado por el usuario.")
            return Ok(result)

        self._finalize(request, result, professionals, output_file)
        result.elapsed_seconds = time.monotonic() - start
        self._write_report(request, result, output_file)
        self._progress.event(
            EventLevel.SUCCESS,
            f"Proceso completado en {result.elapsed_seconds:.1f}s. Salida: {output_file.name}",
        )
        return Ok(result)

    # --- Validación ---

    def _validate(self, request: ProcessRequest) -> None:
        if not request.word_template.exists():
            raise InvalidInputError(f"No existe la plantilla Word: {request.word_template}")
        if request.word_template.suffix.lower() not in WORD_EXTENSIONS:
            raise InvalidInputError("La plantilla debe ser un archivo .docx")
        if not request.excel_files:
            raise InvalidInputError("No se seleccionó ningún archivo Excel.")
        for excel in request.excel_files:
            if excel.suffix.lower() not in EXCEL_EXTENSIONS:
                raise InvalidInputError(f"Archivo Excel no válido: {excel.name}")
        if not request.month.strip():
            raise InvalidInputError("Debe indicarse el mes a procesar.")

    # --- Procesamiento por profesional ---

    def _process_professionals(
        self, request: ProcessRequest, result: ProcessingResult
    ) -> list[Professional]:
        professionals: list[Professional] = []
        total = len(request.excel_files)

        for index, excel in enumerate(request.excel_files):
            if self._progress.is_cancelled():
                break

            professional = self._read_professional(excel, request.month, result)
            self._progress.progress(index + 1, total)
            if professional is None:
                continue

            professionals.append(professional)
            result.professionals_processed += 1
            self._insert_professional_content(professional, result)

        return professionals

    def _read_professional(
        self, excel: Path, month: str, result: ProcessingResult
    ) -> Professional | None:
        try:
            raw = self._deps.excel_reader.read_month(excel, month)
            professional = self._deps.report_builder.build(raw)
        except ODSReporterError as exc:
            message = f"Error al leer '{excel.name}': {exc}"
            result.add_error(message)
            self._progress.event(EventLevel.ERROR, message)
            return None
        except Exception as exc:  # noqa: BLE001 - robustez: un archivo no detiene el resto
            logger.exception("Error inesperado leyendo %s", excel.name)
            message = f"Error inesperado en '{excel.name}': {exc}"
            result.add_error(message)
            self._progress.event(EventLevel.ERROR, message)
            return None

        self._progress.event(
            EventLevel.INFO,
            f"Leído '{excel.name}' ({professional.name or 'profesional desconocido'}): "
            f"{professional.content_activity_count} actividad(es) con contenido.",
        )
        return professional

    def _insert_professional_content(
        self, professional: Professional, result: ProcessingResult
    ) -> None:
        # Origen mostrado en errores/advertencias para poder revisar el archivo culpable.
        origin = self._origin_label(professional)
        for activity in professional.activities:
            if not activity.has_content:
                continue
            try:
                insert = self._deps.word_processor.insert_activity_content(activity)
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
