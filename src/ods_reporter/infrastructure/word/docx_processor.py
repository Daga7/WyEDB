"""Procesador de Word: orquesta lector, escritor y alineador sobre un documento.

Mantiene el estado del documento abierto y de qué entregables ya recibieron
contenido, para poder rellenar al final los que quedaron vacíos con el texto por
defecto. Implementa ``WordProcessorPort``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import docx

from ods_reporter.application.ports.word_processor_port import ActivityInsertResult
from ods_reporter.application.services.entregable_aligner import EntregableAligner
from ods_reporter.domain.entities.activity import Activity
from ods_reporter.domain.exceptions import WordProcessError
from ods_reporter.infrastructure.word.docx_reader import (
    DocxReader,
    WordActivity,
    WordEntregable,
)
from ods_reporter.infrastructure.word.docx_writer import DocxWriter
from ods_reporter.shared.text_utils import is_blank_or_placeholder

logger = logging.getLogger(__name__)


class DocxProcessor:
    """Procesa un documento Word de ODS insertando el contenido del Excel."""

    def __init__(
        self,
        reader: DocxReader | None = None,
        writer: DocxWriter | None = None,
        aligner: EntregableAligner | None = None,
    ) -> None:
        self._reader = reader or DocxReader()
        self._writer = writer or DocxWriter()
        self._aligner = aligner or EntregableAligner()
        self._document: docx.Document | None = None
        self._activities: list[WordActivity] = []
        self._by_ordinal: dict[int, WordActivity] = {}
        # Entregables del Word que ya recibieron contenido (para no sobrescribir
        # ni rellenarlos luego con el texto por defecto).
        self._filled: set[int] = set()

    def open(self, path: Path) -> None:
        try:
            self._document = docx.Document(str(path))
        except Exception as exc:
            raise WordProcessError(f"No se pudo abrir el Word '{path.name}': {exc}") from exc
        self._activities = self._reader.read_activities(self._document)
        self._by_ordinal = {a.ordinal: a for a in self._activities}
        self._filled = set()
        logger.info("Word '%s' abierto: %d actividades.", path.name, len(self._activities))

    def get_activity_ordinals(self) -> list[int]:
        return [a.ordinal for a in self._activities]

    def insert_activity_content(self, activity: Activity) -> ActivityInsertResult:
        word_activity = self._by_ordinal.get(activity.ordinal)
        if word_activity is None:
            return ActivityInsertResult(
                ordinal=activity.ordinal,
                matched=False,
                items_written=0,
                entregables_matched=0,
                entregables_unmatched=len(activity.entregables),
                warnings=(f"La actividad {activity.ordinal} no existe en el Word.",),
            )

        # Solo interesan los entregables del Excel que tienen contenido.
        source = [e for e in activity.entregables if e.has_content]
        if not source:
            return ActivityInsertResult(
                ordinal=activity.ordinal,
                matched=True,
                items_written=0,
                entregables_matched=0,
                entregables_unmatched=0,
            )

        word_entregables = word_activity.entregables

        # "Dividido" se decide por la ESTRUCTURA del Excel: si la actividad tiene
        # una sola fila de entregable, NO está dividida y su contenido va a TODAS
        # las sub-filas del Word. Si tiene varias, cada contenido va a la sub-fila
        # cuyo texto de entregable coincide (las que no casan reciben texto por defecto).
        not_divided = len(activity.entregables) == 1

        items_written = 0
        matched = 0

        if not_divided:
            items = source[0].content_items
            for word_entregable in word_entregables:
                items_written += self._writer.fill_entregable(word_entregable, items)
                self._filled.add(id(word_entregable))
                matched += 1
        else:
            matches = self._aligner.match_each(
                [w.normalized_text for w in word_entregables],
                [e.normalized_text for e in source],
            )
            for word_entregable, source_index in zip(word_entregables, matches, strict=True):
                if source_index is None:
                    continue  # esta sub-fila no casa con ningún entregable -> default
                items = source[source_index].content_items
                items_written += self._writer.fill_entregable(word_entregable, items)
                self._filled.add(id(word_entregable))
                matched += 1

        return ActivityInsertResult(
            ordinal=activity.ordinal,
            matched=True,
            items_written=items_written,
            entregables_matched=matched,
            entregables_unmatched=0,
        )

    def fill_empty_with_default(self, default_text: str) -> int:
        count = 0
        for activity in self._activities:
            for entregable in activity.entregables:
                if id(entregable) in self._filled:
                    continue
                if self._is_slot_empty(entregable):
                    self._writer.set_default_text(entregable, default_text)
                    count += 1
        logger.info("Slots rellenados con texto por defecto: %d", count)
        return count

    def save(self, path: Path) -> None:
        if self._document is None:
            raise WordProcessError("No hay documento abierto para guardar.")
        try:
            self._document.save(str(path))
        except Exception as exc:
            raise WordProcessError(f"No se pudo guardar el Word '{path.name}': {exc}") from exc

    @staticmethod
    def _is_slot_empty(entregable: WordEntregable) -> bool:
        slot = entregable.slot_paragraph
        return slot is not None and is_blank_or_placeholder(slot.text)
