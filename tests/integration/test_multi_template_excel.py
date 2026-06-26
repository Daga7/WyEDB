"""Pruebas: el lector reconoce automáticamente distintas plantillas de Excel.

ODS 11 (con columna ENTREGABLES, numeración romana en el Word) vs ODS 266/HOCOL
(sin columna ENTREGABLES, numeración arábiga, hojas con nombres combinados).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ods_reporter.application.services.report_builder import ReportBuilder
from ods_reporter.infrastructure.excel.openpyxl_reader import OpenpyxlExcelReader

FIXTURES = Path(__file__).parent.parent / "fixtures"
ODS266_EXCEL = FIXTURES / "ODS266_Excel.xlsx"


@pytest.fixture
def reader() -> OpenpyxlExcelReader:
    return OpenpyxlExcelReader()


@pytest.fixture
def ods266_excel() -> Path:
    if not ODS266_EXCEL.exists():
        pytest.skip(f"Falta el fixture: {ODS266_EXCEL}")
    return ODS266_EXCEL


def test_reads_excel_without_entregables_column(
    reader: OpenpyxlExcelReader, ods266_excel: Path
) -> None:
    # ODS 266 no tiene columna ENTREGABLES: cada actividad es su propio entregable.
    report = reader.read_month(ods266_excel, "ABRIL")
    assert report.professional_name != ""
    assert len(report.activities) >= 40
    # Cada actividad tiene exactamente un entregable, con su texto = la actividad.
    for activity in report.activities:
        assert len(activity.entregables) == 1
        assert activity.entregables[0].entregable_text != ""


def test_stops_at_otras_actividades_generic(
    reader: OpenpyxlExcelReader, ods266_excel: Path
) -> None:
    # No debe incluir el bloque "OTRAS ACTIVIDADES SOLICITADAS POR HOCOL".
    report = reader.read_month(ods266_excel, "ABRIL")
    textos = " ".join(a.entregables[0].entregable_text.lower() for a in report.activities)
    assert "otras actividades solicitadas" not in textos


def test_partial_month_sheet_match(reader: OpenpyxlExcelReader, ods266_excel: Path) -> None:
    # "MARZO" debe encontrar la hoja "FEB_MARZO" por coincidencia parcial.
    report = reader.read_month(ods266_excel, "MARZO")
    assert len(report.activities) >= 40


def test_ods11_still_uses_entregables_column() -> None:
    # Regresión: ODS 11 sí tiene columna ENTREGABLES (entregables distintos por actividad).
    excel = FIXTURES / "ODS11_2026_Mayo.xlsx"
    if not excel.exists():
        pytest.skip("Falta el fixture de ODS 11")
    report = OpenpyxlExcelReader().read_month(excel, "MAYO")
    builder = ReportBuilder()
    professional = builder.build(report)
    act4 = next(a for a in professional.activities if a.ordinal == 4)
    # En ODS 11 la actividad 4 tiene 2 entregables con textos distintos.
    assert len(act4.entregables) == 2
    assert act4.entregables[0].entregable_text != act4.entregables[1].entregable_text
