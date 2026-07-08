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

import re

from ods_reporter.domain.value_objects.content_item import ContentItem
from ods_reporter.shared.constants import (
    NO_ACTIVITY_CONTAINS,
    NO_ACTIVITY_EXACT_MARKERS,
    NO_ACTIVITY_SENTENCE_PREFIXES,
    NO_ACTIVITY_SHORT_MAX_WORDS,
    NO_ACTIVITY_SHORT_PREFIXES,
)
from ods_reporter.shared.text_utils import (
    clean_content_line,
    normalize_text,
    strip_leading_bare_number,
)

# Línea que empieza por un número "pelado" + espacio: "1 texto", "12 texto".
_BARE_NUMBERED_LINE_RE = re.compile(r"^\s*\d{1,2}\s+\S")


class ContentNormalizer:
    """Transforma textos crudos de la columna F en ``ContentItem`` limpios."""

    def normalize(self, raw_contents: tuple[str, ...]) -> tuple[ContentItem, ...]:
        """Devuelve los ítems de contenido limpios para una actividad.

        ``raw_contents`` son los textos de F de todas las sub-filas de la actividad.
        """
        items: list[ContentItem] = []
        for raw in raw_contents:
            lines = raw.splitlines() or [raw]
            # Si la celda es una lista con números "pelados" (1 texto, 2 texto, ...),
            # se quitan esos números; si no, se conservan (para no borrar números que
            # son parte real del contenido, como "3 ICA radicados").
            numbered_list = self._is_bare_numbered_list(lines)
            # El filtrado es POR LÍNEA: una celda puede mezclar líneas reales con
            # líneas de "no se requirió"; solo se descartan estas últimas.
            for line in lines:
                clean = clean_content_line(line)
                if numbered_list:
                    clean = strip_leading_bare_number(clean)
                if clean and not self.is_empty_marker(clean):
                    items.append(ContentItem(clean))
        return tuple(items)

    @staticmethod
    def _is_bare_numbered_list(lines: list[str]) -> bool:
        """``True`` si al menos dos líneas empiezan por un número "pelado" + espacio."""
        return sum(1 for line in lines if _BARE_NUMBERED_LINE_RE.match(line)) >= 2

    @staticmethod
    def is_empty_marker(text: str) -> bool:
        """``True`` si el texto indica ausencia de actividad (se debe ignorar).

        Detecta cuatro formas:
          - frases que EMPIEZAN por "no se requirió...";
          - frases que CONTIENEN "no se requirió/solicitó el servicio/producto/esta
            actividad..." (aunque vengan precedidas de "Durante el periodo..." /
            "En el presente periodo...");
          - prefijos "cortos" ("no aplica", "no aplica para este mes"): solo si la
            línea es breve, para no descartar aclaraciones con contenido real;
          - marcadores exactos ("no aplica", "n/a").
        """
        normalized = normalize_text(text).rstrip(".-: ").strip()
        if not normalized:
            return True
        if any(normalized.startswith(prefix) for prefix in NO_ACTIVITY_SENTENCE_PREFIXES):
            return True
        if any(phrase in normalized for phrase in NO_ACTIVITY_CONTAINS):
            return True
        if ContentNormalizer._is_short_no_activity(normalized):
            return True
        return normalized in NO_ACTIVITY_EXACT_MARKERS

    @staticmethod
    def _is_short_no_activity(normalized: str) -> bool:
        """``True`` si la línea empieza por un prefijo corto de no-actividad y es breve.

        Ej.: ``"no aplica para este mes"`` (4 palabras) -> vacío; en cambio
        ``"no aplica para enero, pero se realizo el seguimiento X"`` (largo) se
        conserva por describir actividad real.
        """
        if not any(normalized.startswith(p) for p in NO_ACTIVITY_SHORT_PREFIXES):
            return False
        return len(normalized.split()) <= NO_ACTIVITY_SHORT_MAX_WORDS
