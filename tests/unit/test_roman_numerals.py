"""Pruebas de la conversión de números romanos."""

from __future__ import annotations

import pytest

from ods_reporter.infrastructure.matching.roman_numerals import roman_to_int


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
