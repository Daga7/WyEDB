"""Pruebas de las utilidades de normalización de texto."""

from __future__ import annotations

import pytest

from ods_reporter.shared.text_utils import (
    clean_content_line,
    collapse_whitespace,
    extract_ods_number,
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
        ("7_Instalación de piezómetros", "Instalación de piezómetros"),
        ("12_Seguimiento y revegetalización", "Seguimiento y revegetalización"),
        ("Sin numeral inicial", "Sin numeral inicial"),
        ("media. esto no es numeral", "media. esto no es numeral"),
    ],
)
def test_strip_leading_numeral(entrada: str, esperado: str) -> None:
    assert strip_leading_numeral(entrada) == esperado


def test_strip_leading_numeral_only_strips_once() -> None:
    # Solo se elimina la primera numeración, no las internas.
    assert strip_leading_numeral("1. 2. doble") == "2. doble"


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        # Numeral romano/arábigo sin punto, seguido de espacios (duros o dobles).
        ("xiii\xa0\xa0\xa0 Acompañar la elaboración", "Acompañar la elaboración"),
        ("13  Elaborar informe", "Elaborar informe"),
        ("iv\xa0Direccionar estudios", "Direccionar estudios"),
        # NO se toca una sola letra ni el texto que empieza con espacios simples.
        ("a continuación se detalla", "a continuación se detalla"),
        ("12 unidades entregadas", "12 unidades entregadas"),
    ],
)
def test_strip_leading_numeral_without_separator(entrada: str, esperado: str) -> None:
    assert strip_leading_numeral(entrada) == esperado


@pytest.mark.parametrize(
    ("linea", "esperado"),
    [
        # Guion bajo: el separador más común en los Excel reales.
        ("_Gestión para respuesta", "Gestión para respuesta"),
        ("_ Se elabora informe", "Se elabora informe"),
        # Combinaciones de marcadores: se quitan todas las capas.
        ("_- doble marcador", "doble marcador"),
        ("__doble guion bajo", "doble guion bajo"),
        ("1. - numeral y guion", "numeral y guion"),
        # Viñetas clásicas.
        ("• Seguimiento", "Seguimiento"),
        ("- Radicación ICA", "Radicación ICA"),
        ("* item", "item"),
        # NO se tocan paréntesis ni comillas (parte real del contenido).
        ("(DIR) reunión", "(DIR) reunión"),
        ('informe "BALANCE ODS"', 'informe "BALANCE ODS"'),
        # Guion interno intacto.
        ("Reunión - seguimiento diario", "Reunión - seguimiento diario"),
        # Número real de contenido preservado.
        ("3 ICA radicados", "3 ICA radicados"),
        # Marcador suelto -> vacío.
        ("_- ", ""),
    ],
)
def test_clean_content_line(linea: str, esperado: str) -> None:
    assert clean_content_line(linea) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("3040727 ECP ODS No. 11", "11"),
        ("ODS 12", "12"),
        ("ODS N° 5", "5"),
        ("ods nro. 266", "266"),
        ("ODS No: 7", "7"),
        ("DURACIÓN DE LA ODS", ""),
        ("Orden de Trabajo OT 279", ""),
        ("", ""),
    ],
)
def test_extract_ods_number(texto: str, esperado: str) -> None:
    assert extract_ods_number(texto) == esperado
