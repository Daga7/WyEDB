"""Entidad ``Activity``: una actividad leída del Excel de un profesional.

Contiene el numeral, el texto original (etiqueta) y sus **entregables** (cada uno
con su propio contenido). No realiza el parseo del contenido (eso ocurre en la
capa de aplicación, Fase 5); aquí solo se almacena y se exponen reglas simples.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ods_reporter.domain.entities.entregable import Entregable
from ods_reporter.domain.value_objects.activity_identity import ActivityIdentity
from ods_reporter.domain.value_objects.content_item import ContentItem
from ods_reporter.shared.text_utils import normalize_text, strip_leading_numeral


@dataclass(frozen=True, slots=True)
class Activity:
    """Una actividad de un profesional para un periodo.

    Attributes
    ----------
    ordinal:
        Numeral/posición de la actividad (columna ID del Excel).
    label:
        Texto original de la actividad, tal como aparece en el Excel/Word.
    entregables:
        Entregables de la actividad (una o varias sub-filas). Cada uno con su
        propio contenido.
    """

    ordinal: int
    label: str
    entregables: tuple[Entregable, ...] = field(default_factory=tuple)

    @property
    def identity(self) -> ActivityIdentity:
        """Clave de identidad (numeral + texto normalizado sin numeración)."""
        normalized = normalize_text(strip_leading_numeral(self.label))
        return ActivityIdentity(ordinal=self.ordinal, normalized_label=normalized)

    @property
    def has_content(self) -> bool:
        """``True`` si al menos un entregable tiene contenido."""
        return any(entregable.has_content for entregable in self.entregables)

    @property
    def all_content_items(self) -> tuple[ContentItem, ...]:
        """Todos los ítems de contenido de la actividad (aplanados)."""
        return tuple(
            item for entregable in self.entregables for item in entregable.content_items
        )
