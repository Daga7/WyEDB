"""Pruebas del validador de compatibilidad Excel ↔ plantilla Word."""

from __future__ import annotations

from ods_reporter.application.ports.word_processor_port import WordActivityOverview
from ods_reporter.application.services.ods_validator import OdsCompatibilityValidator
from ods_reporter.domain.entities.activity import Activity
from ods_reporter.domain.entities.professional import Professional

_WORD_LABELS = {
    1: "i. Identificar y analizar requisitos ambientales",
    2: "ii. Elaborar el recurso de reposición cuando aplique",
    3: "iii. Documentar conceptos técnicos ambientales",
    4: "iv. Acompañar visitas de campo y comités",
}

_OTHER_LABELS = {
    1: "Informe de análisis de variables del sistema",
    2: "Matriz de control documental",
    3: "Reporte de auditoría y plan de acción",
    4: "Gestión de peticiones hasta el cierre",
}


def _professional(labels: dict[int, str], ods_number: str = "") -> Professional:
    activities = tuple(Activity(ordinal=o, label=label) for o, label in labels.items())
    return Professional(
        name="Ana Pérez", source_file="a.xlsx", activities=activities, ods_number=ods_number
    )


def _overview(labels: dict[int, str]) -> list[WordActivityOverview]:
    return [
        WordActivityOverview(ordinal=o, label=label, entregable_count=1)
        for o, label in labels.items()
    ]


def test_same_labels_are_compatible() -> None:
    result = OdsCompatibilityValidator().validate(
        _professional(_WORD_LABELS), _overview(_WORD_LABELS), word_ods_number=""
    )
    assert result.compatible is True


def test_minor_wording_differences_are_tolerated() -> None:
    # Numeración distinta, tildes y una palabra cambiada no deben rechazar.
    excel = {
        1: "1) Identificar y analizar requisitos ambientales",
        2: "Elaborar el recurso de reposicion cuando aplique",
        3: "iii. Documentar los conceptos técnicos ambientales",
        4: "iv.  Acompañar visitas de campo y comités",
    }
    result = OdsCompatibilityValidator().validate(
        _professional(excel), _overview(_WORD_LABELS), word_ods_number=""
    )
    assert result.compatible is True


def test_different_ods_numbers_reject_file() -> None:
    result = OdsCompatibilityValidator().validate(
        _professional(_WORD_LABELS, ods_number="3040727 ECP ODS No. 12"),
        _overview(_WORD_LABELS),
        word_ods_number="ODS No. 11",
    )
    assert result.compatible is False
    assert "12" in result.reason and "11" in result.reason


def test_matching_ods_numbers_fall_through_to_labels() -> None:
    result = OdsCompatibilityValidator().validate(
        _professional(_WORD_LABELS, ods_number="ODS No. 11"),
        _overview(_WORD_LABELS),
        word_ods_number="3040727 ECP ODS No. 11",
    )
    assert result.compatible is True


def test_mismatched_labels_reject_file() -> None:
    result = OdsCompatibilityValidator().validate(
        _professional(_OTHER_LABELS), _overview(_WORD_LABELS), word_ods_number=""
    )
    assert result.compatible is False
    assert "enunciados" in result.reason


def test_too_few_comparable_activities_do_not_reject() -> None:
    # Con menos de 3 actividades comparables no hay señal suficiente.
    excel = {1: _OTHER_LABELS[1], 2: _OTHER_LABELS[2]}
    result = OdsCompatibilityValidator().validate(
        _professional(excel), _overview(_WORD_LABELS), word_ods_number=""
    )
    assert result.compatible is True
