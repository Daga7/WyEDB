"""Implementación del lector de Excel con openpyxl.

Lee la hoja de un mes y extrae los metadatos de cabecera y las actividades
(agrupando las que abarcan varias sub-filas). Hace una extracción fiel: no
filtra ni interpreta el contenido (eso lo hace el normalizador en la Fase 5).
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

import openpyxl

from ods_reporter.application.ports.excel_reader_port import (
    RawActivity,
    RawEntregable,
    RawReport,
)
from ods_reporter.domain.exceptions import ExcelReadError, InvalidInputError
from ods_reporter.infrastructure.excel.excel_schema import (
    TableLayout,
    find_professional_name,
    find_table_layout,
    is_stop_marker,
    read_metadata,
)
from ods_reporter.shared.constants import EXCEL_EXTENSIONS, MONTHS

logger = logging.getLogger(__name__)


class OpenpyxlExcelReader:
    """Lector de Excel basado en openpyxl (implementa ``ExcelReaderPort``)."""

    def read_month(self, file_path: Path, month: str) -> RawReport:
        self._validate_file(file_path)

        try:
            workbook = openpyxl.load_workbook(file_path, data_only=True, read_only=False)
        except Exception as exc:  # openpyxl lanza varios tipos según el problema
            raise ExcelReadError(
                f"No se pudo abrir el archivo Excel '{file_path.name}': {exc}"
            ) from exc

        try:
            sheet = self._select_sheet(workbook, month, file_path)
            layout = find_table_layout(sheet)
            metadata = read_metadata(sheet, layout.header_row, source_file=file_path.name)
            # Si el nombre del profesional falta en la hoja del mes, se busca en
            # las demás hojas (algunos profesionales solo lo diligencian en una).
            if not metadata.responsible_professional:
                fallback = self._find_name_in_other_sheets(workbook, month)
                if fallback:
                    metadata = dataclasses.replace(
                        metadata, responsible_professional=fallback
                    )
            activities = self._read_activities(sheet, layout)
        finally:
            workbook.close()

        logger.info(
            "Excel '%s' [%s]: %d actividades leídas (profesional: %s)",
            file_path.name,
            month,
            len(activities),
            metadata.responsible_professional or "desconocido",
        )
        return RawReport(metadata=metadata, activities=activities)

    # --- Validación ---

    @staticmethod
    def _validate_file(file_path: Path) -> None:
        if not file_path.exists():
            raise InvalidInputError(f"El archivo no existe: {file_path}")
        if file_path.suffix.lower() not in EXCEL_EXTENSIONS:
            raise InvalidInputError(
                f"Extensión no válida '{file_path.suffix}'. "
                f"Se esperaba una de: {', '.join(EXCEL_EXTENSIONS)}"
            )

    @staticmethod
    def _find_name_in_other_sheets(workbook: openpyxl.Workbook, current_month: str) -> str:
        """Busca el nombre del profesional en las demás hojas-mes del libro."""
        target = current_month.strip().lower()
        for name in workbook.sheetnames:
            if name.strip().lower() == target:
                continue
            if name.strip().upper() not in MONTHS:
                continue
            found = find_professional_name(workbook[name])
            if found:
                return found
        return ""

    @staticmethod
    def _select_sheet(
        workbook: openpyxl.Workbook, month: str, file_path: Path
    ) -> "openpyxl.worksheet.worksheet.Worksheet":
        # 1) Coincidencia exacta (tolerante a mayúsculas/espacios).
        target = month.strip().lower()
        for name in workbook.sheetnames:
            if name.strip().lower() == target:
                return workbook[name]
        # 2) Coincidencia parcial: el mes está contenido en el nombre de la hoja
        #    (p. ej. "MARZO" dentro de "FEB_MARZO"), o viceversa.
        for name in workbook.sheetnames:
            normalized = name.strip().lower()
            if target and (target in normalized or normalized in target):
                return workbook[name]
        raise ExcelReadError(
            f"El archivo '{file_path.name}' no contiene la hoja del mes '{month}'. "
            f"Hojas disponibles: {', '.join(workbook.sheetnames)}"
        )

    # --- Lectura de la tabla de actividades ---

    def _read_activities(
        self,
        sheet: "openpyxl.worksheet.worksheet.Worksheet",
        layout: TableLayout,
    ) -> tuple[RawActivity, ...]:
        activities: list[RawActivity] = []
        current_ordinal: int | None = None
        current_label: str = ""
        current_entregables: list[RawEntregable] = []

        def flush() -> None:
            if current_ordinal is not None:
                activities.append(
                    RawActivity(
                        ordinal=current_ordinal,
                        label=current_label,
                        entregables=tuple(current_entregables),
                    )
                )

        for row in range(layout.header_row + 1, sheet.max_row + 1):
            id_value = sheet.cell(row=row, column=layout.id_col).value
            label_value = sheet.cell(row=row, column=layout.activities_col).value
            content_value = sheet.cell(row=row, column=layout.description_col).value

            # Fin de la tabla de actividades.
            if is_stop_marker(str(id_value or "")) or is_stop_marker(str(label_value or "")):
                break

            ordinal = self._parse_ordinal(id_value)

            if ordinal is not None:
                # Comienza una nueva actividad: se cierra la anterior.
                flush()
                current_ordinal = ordinal
                current_label = str(label_value).strip() if label_value is not None else ""
                current_entregables = []

            # Cada sub-fila (inicial o de continuación) es un entregable.
            if current_ordinal is not None:
                entregable_text = self._entregable_text(sheet, row, layout, label_value)
                content_text = str(content_value).strip() if content_value else ""
                if entregable_text or content_text:
                    current_entregables.append(
                        RawEntregable(
                            entregable_text=entregable_text,
                            raw_content=content_text,
                        )
                    )

        flush()
        return tuple(activities)

    @staticmethod
    def _entregable_text(
        sheet: "openpyxl.worksheet.worksheet.Worksheet",
        row: int,
        layout: TableLayout,
        label_value: object,
    ) -> str:
        """Texto del entregable de la fila.

        Si la plantilla tiene columna ENTREGABLES, se usa esa. Si no (p. ej. HOCOL),
        la actividad es su propio entregable: se usa el texto de ACTIVIDADES.
        """
        if layout.entregables_col is not None:
            value = sheet.cell(row=row, column=layout.entregables_col).value
            return str(value).strip() if value else ""
        return str(label_value).strip() if label_value else ""

    @staticmethod
    def _parse_ordinal(value: object) -> int | None:
        """Convierte el valor de la columna ID en un entero positivo, o ``None``."""
        if value is None:
            return None
        try:
            number = int(float(str(value).strip()))
        except (ValueError, TypeError):
            return None
        return number if number > 0 else None
