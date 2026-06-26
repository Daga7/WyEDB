"""Pruebas de las utilidades de normalización de texto."""

from __future__ import annotations

import pytest

from ods_reporter.shared.text_utils import (
    collapse_whitespace,
    normalize_text,
    strip_accents,
    strip_leading_numeral,
)


def test_strip_accents_removes_diacritics() -> None:
    assert strip_accents("Educación Ambiental") == "Educacion Ambiental"
    assert strip_accents("Gestión") == "Gestion"
    assert strip_accents("ñandú") == "nandu"


def test_collapse_whitespace() -> None:
    assert collapse_whitespace("  hola   mundo \n nuevo ") == "hola mundo nuevo"


def test_normalize_text_canonical_form() -> None:
    assert normalize_text("  Educación  Ambiental ") == "educacion ambiental"
    assert normalize_text("MANEJO de Residuos") == "manejo de residuos"


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("i. Identificar y analizar", "Identificar y analizar"),
        ("ii.  Elaborar recurso", "Elaborar recurso"),
        ("vii. Documentar conceptos", "Documentar conceptos"),
        ("1) Cargar soporte", "Cargar soporte"),
        ("10. Décima actividad", "Décima actividad"),
        ("a) Primera", "Primera"),
        ("Sin numeral inicial", "Sin numeral inicial"),
        ("media. esto no es numeral", "media. esto no es numeral"),
    ],
)
def test_strip_leading_numeral(entrada: str, esperado: str) -> None:
    assert strip_leading_numeral(entrada) == esperado


def test_strip_leading_numeral_only_strips_once() -> None:
    # Solo se elimina la primera numeración, no las internas.
    assert strip_leading_numeral("1. 2. doble") == "2. doble"
