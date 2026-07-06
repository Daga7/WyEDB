"""Pruebas de la conversión de números romanos."""

from __future__ import annotations

import pytest

from ods_reporter.infrastructure.matching.roman_numerals import int_to_roman, roman_to_int


@pytest.mark.parametrize(
    ("romano", "esperado"),
    [
        ("I", 1),
        ("IV", 4),
        ("V", 5),
        ("IX", 9),
        ("X", 10),
        ("xvi", 16),
        ("XXX", 30),
        ("  iii  ", 3),
        ("XXIX", 29),
    ],
)
def test_roman_to_int_valid(romano: str, esperado: int) -> None:
    assert roman_to_int(romano) == esperado


@pytest.mark.parametrize("invalido", ["", "   ", "abc", "IIII", "VV", "texto", "12"])
def test_roman_to_int_invalid(invalido: str) -> None:
    assert roman_to_int(invalido) is None


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [
        (1, "I"),
        (4, "IV"),
        (9, "IX"),
        (16, "XVI"),
        (29, "XXIX"),
        (30, "XXX"),
        (3999, "MMMCMXCIX"),
    ],
)
def test_int_to_roman(numero: int, esperado: str) -> None:
    assert int_to_roman(numero) == esperado


@pytest.mark.parametrize("fuera_de_rango", [0, -3, 4000])
def test_int_to_roman_out_of_range_falls_back_to_arabic(fuera_de_rango: int) -> None:
    assert int_to_roman(fuera_de_rango) == str(fuera_de_rango)


def test_roundtrip_roman_conversions() -> None:
    for value in range(1, 200):
        assert roman_to_int(int_to_roman(value)) == value
