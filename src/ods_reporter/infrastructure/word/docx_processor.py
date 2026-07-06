"""Procesador de Word: orquesta lector, escritor y alineador sobre un documento.

Mantiene el estado del documento abierto y de qué entregables ya recibieron
contenido, para poder rellenar al final los que quedaron vacíos con el texto por
defecto. Implementa ``WordProcessorPort``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import docx

from ods_reporter.application.ports.word_processor_port import (
    ActivityInsertResult,
    WordActivityOverview,
)
from ods_reporter.domain.value_objects.content_item import ContentItem
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
        self._observaciones: WordEntregable | None = None
        self._by_ordinal: dict[int, WordActivity] = {}
        # Entregables del Word que ya recibieron contenido (para no sobrescribir
        # ni rellenarlos luego con el texto por defecto).
        self._filled: set[int] = set()

    def open(self, path: Path) -> None:
        try:
            self._document = docx.Document(str(path))
        except Exception as exc:
            raise WordProcessError(f"No se pudo abrir el Word '{path.name}': {exc}") from exc
        structure = self._reader.read_structure(self._document)
        self._activities = structure.activities
        self._observaciones = structure.observaciones
        self._by_ordinal = {a.ordinal: a for a in self._activities}
        self._filled = set()
        logger.info(
            "Word '%s' abierto: %d actividades (observaciones: %s).",
            path.name,
            len(self._activities),
            "sí" if self._observaciones else "no",
        )

    def get_activity_ordinals(self) -> list[int]:
        return [a.ordinal for a in self._activities]

    def get_activities_overview(self) -> list[WordActivityOverview]:
        return [
            WordActivityOverview(
                ordinal=a.ordinal, label=a.label, entregable_count=len(a.entregables)
            )
            for a in self._activities
        ]

    def plan_activity_content(self, activity: Activity) -> ActivityInsertResult:
        """Calcula el resultado de insertar ``activity`` sin escribir nada."""
        word_activity = self._by_ordinal.get(activity.ordinal)
        if word_activity is None:
            return self._not_found_result(activity)
        assignments = self._compute_assignments(activity, word_activity)
        return self._build_result(activity, assignments)

    def insert_activity_content(
        self, activity: Activity, target_ordinal: int | None = None
    ) -> ActivityInsertResult:
        manual = target_ordinal is not None
        ordinal = target_ordinal if target_ordinal is not None else activity.ordinal
        word_activity = self._by_ordinal.get(ordinal)
        if word_activity is None:
            return self._not_found_result(activity)

        warnings: tuple[str, ...] = ()
        if manual:
            assignments = self._compute_manual_assignments(activity, word_activity)
            warnings = (
                f"La actividad {activity.ordinal} se insertó manualmente "
                f"en el numeral {ordinal} del Word.",
            )
        else:
            assignments = self._compute_assignments(activity, word_activity)

        for word_entregable, items in assignments:
            self._writer.fill_entregable(word_entregable, items)
            self._filled.add(id(word_entregable))

        return self._build_result(activity, assignments, warnings)

    # --- Cálculo de asignaciones (compartido por plan e inserción) ---

    def _compute_assignments(
        self, activity: Activity, word_activity: WordActivity
    ) -> list[tuple[WordEntregable, tuple[ContentItem, ...]]]:
        """Decide qué ítems van a qué entregable del Word (sin escribir)."""
        source = [e for e in activity.entregables if e.has_content]
        word_entregables = word_activity.entregables
        if not source or not word_entregables:
            return []

        # "Dividido" se decide por la ESTRUCTURA del Excel: si la actividad tiene
        # una sola fila de entregable, NO está dividida y su contenido va a TODAS
        # las sub-filas del Word. Si tiene varias, cada contenido va a la sub-fila
        # cuyo texto de entregable coincide (las que no casan reciben texto por defecto).
        if len(activity.entregables) == 1:
            items = source[0].content_items
            return [(w, items) for w in word_entregables]

        matches = self._aligner.match_each(
            [w.normalized_text for w in word_entregables],
            [e.normalized_text for e in source],
        )
        return [
            (word_entregable, source[index].content_items)
            for word_entregable, index in zip(word_entregables, matches, strict=True)
            if index is not None
        ]

    def _compute_manual_assignments(
        self, activity: Activity, word_activity: WordActivity
    ) -> list[tuple[WordEntregable, tuple[ContentItem, ...]]]:
        """Asignaciones para una reasignación manual a otra actividad del Word.

        Se intenta alinear entregables por texto; el contenido que no case va al
        PRIMER entregable de la actividad elegida (el usuario ya decidió el
        destino: no se pierde nada ni se duplica en todas las sub-filas).
        """
        source = [e for e in activity.entregables if e.has_content]
        word_entregables = word_activity.entregables
        if not source or not word_entregables:
            return []

        matches = self._aligner.match_each(
            [w.normalized_text for w in word_entregables],
            [e.normalized_text for e in source],
        )
        assignments = [
            (word_entregable, source[index].content_items)
            for word_entregable, index in zip(word_entregables, matches, strict=True)
            if index is not None
        ]
        placed = {index for index in matches if index is not None}
        leftover = tuple(
            item
            for index, entregable in enumerate(source)
            if index not in placed
            for item in entregable.content_items
        )
        if leftover:
            assignments.append((word_entregables[0], leftover))
        return assignments

    @staticmethod
    def _not_found_result(activity: Activity) -> ActivityInsertResult:
        return ActivityInsertResult(
            ordinal=activity.ordinal,
            matched=False,
            items_written=0,
            entregables_matched=0,
            entregables_unmatched=len(activity.entregables),
            warnings=(f"La actividad {activity.ordinal} no existe en el Word.",),
        )

    @staticmethod
    def _build_result(
        activity: Activity,
        assignments: list[tuple[WordEntregable, tuple[ContentItem, ...]]],
        warnings: tuple[str, ...] = (),
    ) -> ActivityInsertResult:
        return ActivityInsertResult(
            ordinal=activity.ordinal,
            matched=True,
            items_written=sum(len(items) for _, items in assignments),
            entregables_matched=len(assignments),
            entregables_unmatched=0,
            warnings=warnings,
        )

    # --- Sección de observaciones / actividades adicionales ---

    def has_other_activities_section(self) -> bool:
        return self._observaciones is not None

    def insert_other_activities(self, items: tuple[ContentItem, ...]) -> int:
        """Inserta las actividades adicionales en la sección de observaciones."""
        if self._observaciones is None or not items:
            return 0
        written = self._writer.fill_entregable(self._observaciones, items)
        self._filled.add(id(self._observaciones))
        return written

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
