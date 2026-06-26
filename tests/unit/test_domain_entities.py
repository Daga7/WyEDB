"""Pruebas de las entidades y objetos de valor del dominio."""

from __future__ import annotations

import pytest

from ods_reporter.domain import (
    Activity,
    ActivityIdentity,
    ContentItem,
    Entregable,
    ProcessingResult,
    Professional,
)


def _entregable(text: str, *items: str) -> Entregable:
    return Entregable(
        entregable_text=text,
        content_items=tuple(ContentItem(i) for i in items),
    )


# --- ContentItem ---

def test_content_item_rejects_empty_text() -> None:
    with pytest.raises(ValueError):
        ContentItem("   ")


def test_content_item_equality_by_value() -> None:
    assert ContentItem("Radicación ICA") == ContentItem("Radicación ICA")


# --- ActivityIdentity ---

def test_activity_identity_rejects_negative_ordinal() -> None:
    with pytest.raises(ValueError):
        ActivityIdentity(ordinal=-1, normalized_label="x")


# --- Activity ---

def test_activity_has_content() -> None:
    sin = Activity(ordinal=1, label="i. Identificar", entregables=(_entregable("e1"),))
    con = Activity(
        ordinal=1,
        label="i. Identificar",
        entregables=(_entregable("e1", "hecho"),),
    )
    assert sin.has_content is False
    assert con.has_content is True


def test_activity_with_multiple_entregables() -> None:
    # Mapeo fino: cada entregable conserva su propio contenido.
    act = Activity(
        ordinal=4,
        label="iv. Implementar",
        entregables=(
            _entregable("Cargar en repositorio", "Apoyo en radicación"),
            _entregable("Plan de Acción actualizado"),  # sin contenido
        ),
    )
    assert act.has_content is True
    assert len(act.entregables) == 2
    assert act.entregables[0].has_content is True
    assert act.entregables[1].has_content is False
    assert len(act.all_content_items) == 1


def test_activity_identity_normalizes_label_and_strips_numeral() -> None:
    activity = Activity(ordinal=3, label="iii.  Educación  Ambiental")
    assert activity.identity == ActivityIdentity(ordinal=3, normalized_label="educacion ambiental")


def test_same_text_different_numeral_are_distinct() -> None:
    # Regla de negocio: mismo texto, distinto numeral => identidades diferentes.
    a = Activity(ordinal=1, label="i. Plan de acción")
    b = Activity(ordinal=2, label="ii. Plan de acción")
    assert a.identity != b.identity


# --- Professional ---

def test_professional_counts_only_activities_with_content() -> None:
    prof = Professional(
        name="Ana María Ospina",
        source_file="ods11_ana.xlsx",
        activities=(
            Activity(ordinal=1, label="i. A", entregables=(_entregable("e", "x"),)),
            Activity(ordinal=2, label="ii. B", entregables=(_entregable("e"),)),  # sin contenido
            Activity(ordinal=3, label="iii. C", entregables=(_entregable("e", "y"),)),
        ),
    )
    assert prof.content_activity_count == 2
    assert prof.has_no_activities is False
    assert len(prof.activities_with_content) == 2


def test_professional_without_activities() -> None:
    prof = Professional(name="Sin Datos", source_file="vacio.xlsx", activities=())
    assert prof.has_no_activities is True


# --- ProcessingResult ---

def test_processing_result_errors_and_warnings() -> None:
    result = ProcessingResult()
    assert result.has_errors is False
    assert result.has_warnings is False
    result.add_warning("aviso")
    result.add_error("fallo")
    assert result.warnings == ["aviso"]
    assert result.errors == ["fallo"]
    assert result.has_errors is True
    assert result.has_warnings is True


def test_processing_result_default_counters() -> None:
    result = ProcessingResult()
    assert result.professionals_processed == 0
    assert result.activities_with_content == 0
    assert result.items_written == 0
    assert result.default_slots_filled == 0
    assert result.cancelled is False
