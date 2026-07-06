"""Conversión de números romanos.

El documento Word numera las actividades con romanos ("I", "II", "iii"...),
mientras que el Excel usa arábigos en la columna ID. Para emparejar por numeral
hace falta convertir los romanos a enteros.
"""

from __future__ import annotations

import re

_ROMAN_VALUES: dict[str, int] = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}

# Valida un romano canónico (1..3999). Evita aceptar cadenas arbitrarias.
_ROMAN_PATTERN = re.compile(
    r"^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE,
)


_INT_TO_ROMAN: tuple[tuple[int, str], ...] = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


def int_to_roman(value: int) -> str:
    """Convierte un entero a romano en mayúsculas (para mostrar numerales).

    Fuera del rango representable (1..3999) devuelve el número en arábigo,
    de modo que siempre haya algo legible que mostrar.
    """
    if not 1 <= value <= 3999:
        return str(value)
    pieces: list[str] = []
    remaining = value
    for number, symbol in _INT_TO_ROMAN:
        while remaining >= number:
            pieces.append(symbol)
            remaining -= number
    return "".join(pieces)


def roman_to_int(value: str) -> int | None:
    """Convierte un romano (mayúsculas o minúsculas) a entero, o ``None``.

    Acepta texto con espacios alrededor. Devuelve ``None`` si no es un romano
    válido (incluida la cadena vacía).

    Ejemplos:
        ``"IV"`` -> 4 · ``"xvi"`` -> 16 · ``"abc"`` -> ``None``
    """
    cleaned = value.strip().upper()
    if not cleaned or not _ROMAN_PATTERN.match(cleaned):
        return None

    total = 0
    previous = 0
    for char in reversed(cleaned):
        current = _ROMAN_VALUES[char]
        if current < previous:
            total -= current
        else:
            total += current
            previous = current
    return total
