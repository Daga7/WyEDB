"""Pruebas del formateador de resumen."""

from __future__ import annotations

from ods_reporter.application.services.report_formatter import ReportFormatter
from ods_reporter.domain.entities.processing_result import ProcessingResult, ProfessionalAudit


def _result(**kwargs: object) -> ProcessingResult:
    return ProcessingResult(**kwargs)  # type: ignore[arg-type]


def test_format_includes_key_metrics() -> None:
    result = _result(
        professionals_processed=2,
        activities_with_content=9,
        items_written=12,
        default_slots_filled=16,
        elapsed_seconds=0.81,
    )
    text = ReportFormatter().format(result, month="MAYO")
    assert "MAYO" in text
    assert "Profesionales procesados : 2" in text
    assert "Actividades con contenido: 9" in text
    assert "Viñetas insertadas       : 12" in text
    assert "completado correctamente" in text


def test_format_shows_audit() -> None:
    result = _result(
        audit=ProfessionalAudit(
            without_activities=("Juan Pérez",),
            below_threshold=(("Ana Gómez", 3),),
        )
    )
    text = ReportFormatter().format(result)
    assert "Juan Pérez" in text
    assert "Ana Gómez (3)" in text


def test_format_reports_errors() -> None:
    result = _result()
    result.add_error("Falló la lectura de X.xlsx")
    text = ReportFormatter().format(result)
    assert "ERRORES (1)" in text
    assert "Falló la lectura de X.xlsx" in text
    assert "CON ERRORES" in text


def test_format_cancelled() -> None:
    result = _result(cancelled=True)
    text = ReportFormatter().format(result)
    assert "CANCELADO" in text
    assert "incompleto" in text
