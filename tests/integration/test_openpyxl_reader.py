"""Pruebas de integración del lector de Excel contra el archivo real."""

from __future__ import annotations

from pathlib import Path

import pytest

from ods_reporter.domain.exceptions import ExcelReadError, InvalidInputError
from ods_reporter.infrastructure.excel.openpyxl_reader import OpenpyxlExcelReader


@pytest.fixture
def reader() -> OpenpyxlExcelReader:
    return OpenpyxlExcelReader()


def test_reads_metadata(reader: OpenpyxlExcelReader, excel_fixture: Path) -> None:
    report = reader.read_month(excel_fixture, "MAYO")
    assert report.professional_name == "Ana María Ospina Villanueva"
    assert "11" in report.metadata.ods_number
    assert report.source_file == excel_fixture.name


def test_reads_all_30_activities(reader: OpenpyxlExcelReader, excel_fixture: Path) -> None:
    report = reader.read_month(excel_fixture, "MAYO")
    assert len(report.activities) == 30
    ordinals = [a.ordinal for a in report.activities]
    assert ordinals == list(range(1, 31))


def test_excludes_otras_actividades_section(
    reader: OpenpyxlExcelReader, excel_fixture: Path
) -> None:
    report = reader.read_month(excel_fixture, "MAYO")
    labels = " ".join(a.label.lower() for a in report.activities)
    assert "otras actividades solicitadas" not in labels


def test_multirow_activity_keeps_entregables_separate(
    reader: OpenpyxlExcelReader, excel_fixture: Path
) -> None:
    # La actividad 4 abarca 2 sub-filas/entregables: el contenido NO se combina.
    report = reader.read_month(excel_fixture, "MAYO")
    act4 = next(a for a in report.activities if a.ordinal == 4)
    assert len(act4.entregables) == 2
    # El primer entregable tiene el contenido real; el segundo, el marcador.
    joined = " ".join(e.raw_content for e in act4.entregables)
    assert "Apoyo en Radicación de 3 ICA" in joined
    assert any("no se requir" in e.raw_content.lower() for e in act4.entregables)


def test_activity_label_preserved(reader: OpenpyxlExcelReader, excel_fixture: Path) -> None:
    report = reader.read_month(excel_fixture, "MAYO")
    act1 = next(a for a in report.activities if a.ordinal == 1)
    assert "Identificar" in act1.label


def test_empty_month_reads_activities_without_real_content(
    reader: OpenpyxlExcelReader, excel_fixture: Path
) -> None:
    # JUNIO no tiene contenido real: todas las F son el marcador "no se requirió".
    report = reader.read_month(excel_fixture, "JUNIO")
    assert len(report.activities) == 30
    todas_marcador = all(
        all(
            "no se requir" in e.raw_content.lower() or not e.raw_content
            for e in a.entregables
        )
        for a in report.activities
    )
    assert todas_marcador


def test_missing_sheet_raises(reader: OpenpyxlExcelReader, excel_fixture: Path) -> None:
    with pytest.raises(ExcelReadError):
        reader.read_month(excel_fixture, "MES_INEXISTENTE")


def test_missing_file_raises(reader: OpenpyxlExcelReader, tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError):
        reader.read_month(tmp_path / "no_existe.xlsx", "MAYO")


def test_invalid_extension_raises(reader: OpenpyxlExcelReader, tmp_path: Path) -> None:
    fake = tmp_path / "archivo.txt"
    fake.write_text("contenido")
    with pytest.raises(InvalidInputError):
        reader.read_month(fake, "MAYO")
