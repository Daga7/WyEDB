"""Contenedor de inyección de dependencias.

Cablea las implementaciones concretas de infraestructura con el caso de uso.
Mantener este cableado en un único lugar facilita sustituir piezas (por ejemplo,
en pruebas) sin tocar el resto de la aplicación.
"""

from __future__ import annotations

from ods_reporter.application.ports.progress_port import ProgressPort
from ods_reporter.application.use_cases.process_ods import ProcessODSUseCase
from ods_reporter.infrastructure.filesystem.file_service import FileService
from ods_reporter.infrastructure.readers.report_reader_router import ReportReaderRouter
from ods_reporter.infrastructure.reporting.report_writer import ReportWriter
from ods_reporter.infrastructure.word.docx_processor import DocxProcessor


def build_use_case(progress: ProgressPort) -> ProcessODSUseCase:
    """Construye el caso de uso principal con todas sus dependencias reales."""
    return ProcessODSUseCase(
        # Lector enrutado: Excel (.xlsx/.xlsm) o Word de profesional (.docx).
        excel_reader=ReportReaderRouter(),
        word_processor=DocxProcessor(),
        file_service=FileService(),
        progress=progress,
        report_writer=ReportWriter(),
    )
