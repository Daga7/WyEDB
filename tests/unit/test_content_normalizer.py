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
        ("○ Círculo", "Círculo"),
        ("º Otro círculo", "Otro círculo"),
        ("* Asterisco", "Asterisco"),
        ("1. Cargar soporte", "Cargar soporte"),
        ("  2)   Revisar  ", "Revisar"),
        ("Radicación   de    3   ICA  ", "Radicación de 3 ICA"),  # colapsa espacios
        ("Sin viñeta", "Sin viñeta"),
    ],
)
def test_clean_content_line(entrada: str, esperado: str) -> None:
    assert clean_content_line(entrada) == esperado


def test_bare_numbered_list_is_stripped(normalizer: ContentNormalizer) -> None:
    raw = ("1 Cargar soporte\n2 Revisar documento\n3 Radicar",)
    items = normalizer.normalize(raw)
    assert [i.text for i in items] == ["Cargar soporte", "Revisar documento", "Radicar"]


def test_leading_number_in_real_content_is_kept(normalizer: ContentNormalizer) -> None:
    # No es una lista: "3 ICA radicados" debe conservar el número.
    raw = ("3 ICA radicados ante la autoridad ambiental",)
    items = normalizer.normalize(raw)
    assert items[0].text == "3 ICA radicados ante la autoridad ambiental"


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
        # Prefijo corto "no aplica ..." (ODS 17).
        "No aplica para este mes",
        "No aplica para el periodo",
        # Frase exacta pedida por el usuario y sus variantes reales.
        "No se solicitó esta actividad durante el periodo en reporte",
        "En el presente periodo no se solicitó la actividad por parte de Ecopetrol S.A.",
        "No se solicitó esta actividd durante la vigencia reportada",  # errata real
        "La actividad no fue solicitada durante el periodo",
        # Variantes reales de "no hubo trabajo en este numeral".
        "Durante el periodo de reporte no se realizaron este tipo de actividades.",
        "Durante el mes de junio no se ejecutaron actividades relacionadas con este numeral",
        "Durante el periodo no se desarrollaron actividades asociadas, sin embargo se estuvo atento",
        "Para el presente periodo no se ejecutó la actividad",
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
        # "no aplica" seguido de contenido REAL y extenso: NO es marcador.
        "No aplica para enero pero se realizó la gestión",
        "No aplica el trámite anterior, pero se elaboró el informe de seguimiento del PAP",
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
