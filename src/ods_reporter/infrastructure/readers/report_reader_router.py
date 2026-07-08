"""Enrutador de lectores de reportes por tipo de archivo.

Implementa el mismo contrato que un lector (``ExcelReaderPort``) y delega en
el lector adecuado según la extensión: Excel (.xlsx/.xlsm) u Word (.docx).
Gracias a esto el caso de uso no distingue formatos: cualquier archivo de
profesional entra por el mismo puerto y produce el mismo ``RawReport``.
"""

from __future__ import annotations

from pathlib import Path

from ods_reporter.application.ports.excel_reader_port import ExcelReaderPort, RawReport
from ods_reporter.infrastructure.excel.openpyxl_reader import OpenpyxlExcelReader
from ods_reporter.infrastructure.word.docx_source_reader import DocxSourceReader
from ods_reporter.shared.constants import WORD_EXTENSIONS


class ReportReaderRouter:
    """Delegación por extensión: Excel → openpyxl, Word → lector de Word."""

    def __init__(
        self,
        excel_reader: ExcelReaderPort | None = None,
        word_reader: ExcelReaderPort | None = None,
    ) -> None:
        self._excel = excel_reader or OpenpyxlExcelReader()
        self._word = word_reader or DocxSourceReader()

    def read_month(self, file_path: Path, month: str) -> RawReport:
        if file_path.suffix.lower() in WORD_EXTENSIONS:
            return self._word.read_month(file_path, month)
        return self._excel.read_month(file_path, month)
