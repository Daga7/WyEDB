"""Integración: construcción del Professional del dominio desde el Excel real."""

from __future__ import annotations

from pathlib import Path

import pytest

from ods_reporter.application.services.report_builder import ReportBuilder
from ods_reporter.infrastructure.excel.openpyxl_reader import OpenpyxlExcelReader


@pytest.fixture
def reader() -> OpenpyxlExcelReader:
    return OpenpyxlExcelReader()


@pytest.fixture
def builder() -> ReportBuilder:
    return ReportBuilder()


def test_builds_professional_from_real_excel(
    reader: OpenpyxlExcelReader, builder: ReportBuilder, excel_fixture: Path
) -> None:
    raw = reader.read_month(excel_fixture, "MAYO")
    professional = builder.build(raw)

    assert professional.name == "Ana María Ospina Villanueva"
    assert len(professional.activities) == 30
    # En mayo hay varias actividades con contenido real.
    assert professional.content_activity_count > 0
    assert professional.has_no_activities is False


def test_activity_4_maps_content_per_entregable(
    reader: OpenpyxlExcelReader, builder: ReportBuilder, excel_fixture: Path
) -> None:
    raw = reader.read_month(excel_fixture, "MAYO")
    professional = builder.build(raw)
    act4 = next(a for a in professional.activities if a.ordinal == 4)
    # Mapeo fino: el 1er entregable tiene contenido real; el 2º quedó vacío.
    assert len(act4.entregables) == 2
    assert act4.entregables[0].has_content is True
    assert act4.entregables[1].has_content is False
    joined = " ".join(i.text for i in act4.all_content_items)
    assert "Apoyo en Radicación de 3 ICA" in joined
    assert not any("no se requir" in i.text.lower() for i in act4.all_content_items)


def test_empty_month_yields_no_content_activities(
    reader: OpenpyxlExcelReader, builder: ReportBuilder, excel_fixture: Path
) -> None:
    raw = reader.read_month(excel_fixture, "JUNIO")
    professional = builder.build(raw)
    assert professional.has_no_activities is True
    assert professional.content_activity_count == 0
