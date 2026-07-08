"""Pruebas del remapeador de numerales por enunciado (modo Word → Word)."""

from __future__ import annotations

from ods_reporter.application.ports.word_processor_port import WordActivityOverview
from ods_reporter.application.services.activity_remapper import ActivityLabelRemapper
from ods_reporter.domain.entities.activity import Activity
from ods_reporter.domain.entities.entregable import Entregable
from ods_reporter.domain.entities.professional import Professional
from ods_reporter.domain.value_objects.content_item import ContentItem


def _activity(ordinal: int, label: str, *, with_content: bool = True) -> Activity:
    items = (ContentItem("Algo realizado"),) if with_content else ()
    return Activity(
        ordinal=ordinal,
        label=label,
        entregables=(Entregable(entregable_text="Informe", content_items=items),),
    )


def _professional(*activities: Activity) -> Professional:
    return Professional(
        name="Ana", source_file="reporte.docx", activities=tuple(activities)
    )


_OVERVIEW = [
    WordActivityOverview(ordinal=1, label="Identificar requisitos ambientales", entregable_count=1),
    WordActivityOverview(ordinal=2, label="Elaborar conceptos técnicos", entregable_count=1),
    WordActivityOverview(ordinal=3, label="Acompañar visitas de campo", entregable_count=1),
]


def test_remap_rewrites_ordinal_by_label() -> None:
    professional = _professional(
        _activity(1, "Acompañar visitas de campo"),  # en la plantilla es la 3
        _activity(2, "Identificar requisitos ambientales"),  # en la plantilla es la 1
    )

    remapped, warnings = ActivityLabelRemapper().remap(professional, _OVERVIEW)

    assert [a.ordinal for a in remapped.activities] == [3, 1]
    assert len(warnings) == 2
    assert all("se emparejó por su enunciado" in w for w in warnings)


def test_remap_keeps_ordinal_when_already_aligned() -> None:
    professional = _professional(_activity(2, "Elaborar conceptos técnicos"))

    remapped, warnings = ActivityLabelRemapper().remap(professional, _OVERVIEW)

    assert remapped.activities[0].ordinal == 2
    assert warnings == ()


def test_remap_tolerates_small_wording_differences() -> None:
    professional = _professional(
        _activity(1, "Identificación de los requisitos ambientales")
    )

    remapped, _ = ActivityLabelRemapper().remap(professional, _OVERVIEW)

    assert remapped.activities[0].ordinal == 1


def test_unmatched_activity_with_colliding_ordinal_gets_synthetic() -> None:
    professional = _professional(_activity(2, "Gestión de peticiones de otro contrato"))

    remapped, warnings = ActivityLabelRemapper().remap(professional, _OVERVIEW)

    ordinal = remapped.activities[0].ordinal
    assert ordinal not in {1, 2, 3}  # nunca se queda en un numeral de la plantilla
    assert any("no coincide con ninguna" in w for w in warnings)


def test_each_template_activity_is_assigned_once() -> None:
    professional = _professional(
        _activity(1, "Identificar requisitos ambientales"),
        _activity(2, "Identificar requisitos ambientales (duplicada)"),
    )

    remapped, _ = ActivityLabelRemapper().remap(professional, _OVERVIEW)

    ordinals = [a.ordinal for a in remapped.activities]
    assert len(set(ordinals)) == len(ordinals)
    assert ordinals[0] == 1  # la de mayor similitud gana el destino


def test_empty_overview_returns_professional_unchanged() -> None:
    professional = _professional(_activity(1, "Cualquiera"))
    remapped, warnings = ActivityLabelRemapper().remap(professional, [])
    assert remapped is professional
    assert warnings == ()
