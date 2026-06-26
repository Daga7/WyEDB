"""Normalizador del contenido de la columna F.

Convierte los textos crudos extraídos del Excel en una lista plana de
``ContentItem`` lista para insertarse en el Word. Aplica las reglas de negocio:

  1. Descarta los textos que indican "no se requirió la actividad".
  2. Parte las celdas multilínea (saltos de línea) en líneas independientes.
  3. Limpia de cada línea su numeración o viñeta inicial.
  4. Descarta líneas vacías.

Por decisión del usuario, **no** se eliminan ítems duplicados.
"""

from __future__ import annotations

from ods_reporter.domain.value_objects.content_item import ContentItem
from ods_reporter.shared.constants import (
    NO_ACTIVITY_EXACT_MARKERS,
    NO_ACTIVITY_SENTENCE_PREFIXES,
)
from ods_reporter.shared.text_utils import clean_content_line, normalize_text


class ContentNormalizer:
    """Transforma textos crudos de la columna F en ``ContentItem`` limpios."""

    def normalize(self, raw_contents: tuple[str, ...]) -> tuple[ContentItem, ...]:
        """Devuelve los ítems de contenido limpios para una actividad.

        ``raw_contents`` son los textos de F de todas las sub-filas de la actividad.
        """
        items: list[ContentItem] = []
        for raw in raw_contents:
            if self.is_empty_marker(raw):
                continue
            for line in raw.splitlines():
                clean = clean_content_line(line)
                if clean and not self.is_empty_marker(clean):
                    items.append(ContentItem(clean))
        return tuple(items)

    @staticmethod
    def is_empty_marker(text: str) -> bool:
        """``True`` si el texto indica ausencia de actividad (se debe ignorar)."""
        normalized = normalize_text(text).rstrip(".-: ").strip()
        if not normalized:
            return True
        if any(normalized.startswith(prefix) for prefix in NO_ACTIVITY_SENTENCE_PREFIXES):
            return True
        return normalized in NO_ACTIVITY_EXACT_MARKERS
