"""Entidad ``Entregable``: un entregable de una actividad y su contenido.

Una actividad puede tener varios entregables (sub-filas en el Excel / sub-filas
en el Word). Cada entregable tiene su propio texto descriptivo y su propio
contenido. El mapeo Excel↔Word se hace **por entregable** (alineando por su
texto), por lo que esta entidad es la unidad de inserción real en el Word.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ods_reporter.domain.value_objects.content_item import ContentItem
from ods_reporter.shared.text_utils import normalize_text


@dataclass(frozen=True, slots=True)
class Entregable:
    """Un entregable con su contenido ya normalizado.

    Attributes
    ----------
    entregable_text:
        Texto del entregable (columna ENTREGABLES del Excel). Es la clave para
        alinear con la sub-fila correspondiente del Word.
    content_items:
        Ítems de contenido para este entregable (de su celda F). Vacío si no se
        diligenció.
    """

    entregable_text: str
    content_items: tuple[ContentItem, ...] = field(default_factory=tuple)

    @property
    def has_content(self) -> bool:
        return len(self.content_items) > 0

    @property
    def normalized_text(self) -> str:
        """Texto del entregable normalizado, para emparejar con el Word."""
        return normalize_text(self.entregable_text)
