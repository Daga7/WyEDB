"""Objeto de valor que identifica de forma única a una actividad.

La identidad combina el **numeral** (su posición) con el **texto normalizado**.
El numeral es necesario porque pueden existir actividades con el mismo texto pero
distinto numeral; el texto normalizado permite comparaciones robustas.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActivityIdentity:
    """Clave de identidad de una actividad: numeral + texto normalizado.

    Al ser inmutable y comparable por valor, puede usarse como clave de diccionario
    o de conjunto para localizar actividades.
    """

    ordinal: int
    normalized_label: str

    def __post_init__(self) -> None:
        if self.ordinal < 0:
            raise ValueError("El numeral (ordinal) no puede ser negativo.")
