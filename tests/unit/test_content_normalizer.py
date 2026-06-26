"""Pruebas del normalizador de contenido y la limpieza de líneas."""

from __future__ import annotations

import pytest

from ods_reporter.application.services.content_normalizer import ContentNormalizer
from ods_reporter.shared.text_utils import clean_content_line


@pytest.fixture
def normalizer() -> ContentNormalizer:
    return ContentNormalizer()


# --- Limpieza de línea ---

@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("- Radicación ICA", "Radicación ICA"),
        ("• Seguimiento", "Seguimiento"),
        ("1. Cargar soporte", "Cargar soporte"),
        ("  2)   Revisar  ", "Revisar"),
        ("Sin viñeta", "Sin viñeta"),
    ],
)
def test_clean_content_line(entrada: str, esperado: str) -> None:
    assert clean_content_line(entrada) == esperado


# --- Detección de "vacío" ---

@pytest.mark.parametrize(
    "texto",
    [
        "No se requiriò esta actividad para el periodo reportado.",
        "No se requirió esta actividad",
        "  no se requirio el servicio  ",
        # Frases que NO empiezan por "no se requirió" pero lo contienen:
        "Durante el periodo de reporte no se requirió el servicio",
        "En el presente periodo no se requirió el servicio, sin embargo, se estuvo presto",
        "En el presente periodo no se requirió el producto. Sin embargo se estuvo presto",
        "Durante el periodo de reporte la actividad no fue requerida",
        "La actividad no fue requerida durante el periodo relacionado",
        "Durante el periodo comprendido no fue requirerido de mi servicio; sin embargo, se estuvo presta",
        "En este mes No se Aplico este Recurso No obstante esta Disponible",
        "No se ejecutaron acciones para el mes. Por lo tanto, no fue requerdida",
        "No aplica",
        "N/A",
        "-",
        "   ",
    ],
)
def test_is_empty_marker_true(normalizer: ContentNormalizer, texto: str) -> None:
    assert normalizer.is_empty_marker(texto) is True


@pytest.mark.parametrize(
    "texto",
    [
        "Apoyo en Radicación de 3 ICA",
        "No aplica para enero pero se realizó la gestión",  # no es marcador exacto
        "Se socializa presentación",
    ],
)
def test_is_empty_marker_false(normalizer: ContentNormalizer, texto: str) -> None:
    assert normalizer.is_empty_marker(texto) is False


# --- Normalización completa ---

def test_skips_markers_and_keeps_real_content(normalizer: ContentNormalizer) -> None:
    raw = (
        "Apoyo en Radicación de 3 ICA",
        "No se requiriò esta actividad para el periodo reportado.",
    )
    items = normalizer.normalize(raw)
    assert len(items) == 1
    assert items[0].text == "Apoyo en Radicación de 3 ICA"


def test_splits_multiline_cell_and_strips_numbering(normalizer: ContentNormalizer) -> None:
    raw = ("1. Radicación de ICA\n2. Seguimiento a trámites\n3. Revisión documental",)
    items = normalizer.normalize(raw)
    assert [i.text for i in items] == [
        "Radicación de ICA",
        "Seguimiento a trámites",
        "Revisión documental",
    ]


def test_keeps_duplicates(normalizer: ContentNormalizer) -> None:
    # Decisión del usuario: NO se eliminan duplicados.
    raw = ("Se apoyó la visita", "Se apoyó la visita")
    items = normalizer.normalize(raw)
    assert len(items) == 2


def test_mixed_empty_lines_within_cell(normalizer: ContentNormalizer) -> None:
    raw = ("- Tarea real\n- No se requirió esta actividad\n- Otra tarea",)
    items = normalizer.normalize(raw)
    assert [i.text for i in items] == ["Tarea real", "Otra tarea"]


def test_empty_input_returns_empty(normalizer: ContentNormalizer) -> None:
    assert normalizer.normalize(()) == ()
