"""Objeto de valor que representa un único ítem de contenido a insertar en el Word.

Un ítem corresponde a una línea de la columna F del Excel ya normalizada (sin la
numeración original). En el documento se renderiza como un punto con guion.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContentItem:
    """Una línea de contenido lista para insertarse como ítem con guion.

    El texto se almacena ya limpio (sin numeración inicial ni espacios sobrantes);
    la normalización la realiza la capa de aplicación (Fase 5).
    """

    text: str

    def __post_init__(self) -> None:
        if not self.text or not self.text.strip():
            raise ValueError("ContentItem no puede tener texto vacío.")
