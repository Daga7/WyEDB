"""Procesador de Word: orquesta lector, escritor y alineador sobre un documento.

Mantiene el estado del documento abierto y de qué entregables ya recibieron
contenido, para poder rellenar al final los que quedaron vacíos con el texto por
defecto. Implementa ``WordProcessorPort``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import docx
from rapidfuzz import fuzz

from ods_reporter.application.ports.word_processor_port import (
    ActivityInsertResult,
    WordActivityOverview,
)
from ods_reporter.domain.value_objects.content_item import ContentItem
from ods_reporter.shared.text_utils import normalize_text, strip_leading_numeral

# Umbral por debajo del cual el enunciado del Excel y el del Word se consideran
# actividades DISTINTAS aunque compartan numeral (calibrado con datos reales:
# misma ODS ~100 de similitud; ODS distinta ~29).
_LABEL_SIMILARITY_THRESHOLD = 60.0
# Proporción mínima de tokens de nombre compartidos para asignar un profesional a
# una sección del Word (0-100). "Jhann Tellez" vs "Jhann Stive Téllez" -> 100
# (ambos tokens del Word están en el Excel); un desconocido -> 0.
_NAME_MATCH_THRESHOLD = 50.0
from ods_reporter.application.services.entregable_aligner import EntregableAligner
from ods_reporter.domain.entities.activity import Activity
from ods_reporter.domain.exceptions import WordProcessError
from ods_reporter.infrastructure.word.docx_reader import (
    DocxReader,
    WordActivity,
    WordEntregable,
    find_ods_number,
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
        self._ods_number: str = ""
        self._by_ordinal: dict[int, WordActivity] = {}
        # Plantillas divididas por profesional (p. ej. ODS 17): un mapa por grupo
        # {group_index -> {ordinal -> WordActivity}} y la lista de grupos con su
        # nombre. ``_claimed`` recuerda qué grupo se asignó a cada profesional para
        # que dos profesionales no compitan por la misma sección.
        self._groups: dict[int, dict[int, WordActivity]] = {}
        self._group_names: dict[int, str] = {}
        self._claimed: dict[str, int] = {}
        # Entregables del Word que ya recibieron contenido (para no sobrescribir
        # ni rellenarlos luego con el texto por defecto).
        self._filled: set[int] = set()

    @property
    def _has_professional_groups(self) -> bool:
        """``True`` si la plantilla divide las actividades por profesional."""
        return len(self._group_names) > 1

    def open(self, path: Path) -> None:
        try:
            self._document = docx.Document(str(path))
        except Exception as exc:
            raise WordProcessError(f"No se pudo abrir el Word '{path.name}': {exc}") from exc
        structure = self._reader.read_structure(self._document)
        self._activities = structure.activities
        self._observaciones = structure.observaciones
        self._ods_number = find_ods_number(self._document)
        self._by_ordinal = {a.ordinal: a for a in self._activities}
        self._build_groups()
        self._claimed = {}
        self._filled = set()
        logger.info(
            "Word '%s' abierto: %d actividades (observaciones: %s).",
            path.name,
            len(self._activities),
            "sí" if self._observaciones else "no",
        )

    # --- Grupos por profesional (plantillas tipo ODS 17) ---

    def _build_groups(self) -> None:
        """Agrupa las actividades por ``group_index`` (sección de profesional)."""
        self._groups = {}
        self._group_names = {}
        for activity in self._activities:
            group = self._groups.setdefault(activity.group_index, {})
            # A igual numeral dentro del grupo gana la primera (no debería repetirse).
            group.setdefault(activity.ordinal, activity)
            self._group_names.setdefault(activity.group_index, activity.professional_name)

    def _resolve_group(self, professional_name: str) -> tuple[int, str | None]:
        """Devuelve (group_index, advertencia) para un profesional.

        Empareja el nombre del Excel con la sección del Word por tokens de nombre
        compartidos. Si ninguna casa, toma la primera sección aún no reclamada
        (con advertencia). Cada sección se reclama una sola vez.
        """
        key = normalize_text(professional_name)
        if key in self._claimed:
            return self._claimed[key], None

        best_group: int | None = None
        best_score = 0.0
        for group_index, name in self._group_names.items():
            if group_index in self._claimed.values():
                continue
            score = self._name_similarity(professional_name, name)
            if score > best_score:
                best_score = score
                best_group = group_index

        if best_group is not None and best_score >= _NAME_MATCH_THRESHOLD:
            self._claimed[key] = best_group
            return best_group, None

        # Sin coincidencia clara: primera sección libre (para no perder contenido).
        free = [g for g in sorted(self._group_names) if g not in self._claimed.values()]
        if free:
            self._claimed[key] = free[0]
            warning = (
                f"El profesional '{professional_name}' no coincide con ninguna "
                f"sección del Word; su contenido se colocó en la sección "
                f"'{self._group_names[free[0]] or f'#{free[0]}'}'. Verifíquelo."
            )
            return free[0], warning

        # No quedan secciones libres: se reutiliza la mejor aunque esté reclamada.
        fallback = best_group if best_group is not None else next(iter(self._group_names))
        self._claimed[key] = fallback
        warning = (
            f"El profesional '{professional_name}' no tiene una sección propia "
            f"disponible en el Word; se reutilizó '{self._group_names.get(fallback, '')}'."
        )
        return fallback, warning

    @staticmethod
    def _name_similarity(excel_name: str, word_name: str) -> float:
        """Similitud entre nombres tolerante a nombres/apellidos omitidos.

        Usa la proporción de tokens del nombre del Word (normalmente el más corto:
        "Jhann Tellez") presentes en el del Excel ("Jhann Stive Téllez"). Así un
        Word abreviado casa aunque el Excel traiga nombres intermedios.
        """
        excel_tokens = set(normalize_text(excel_name).split())
        word_tokens = set(normalize_text(word_name).split())
        if not excel_tokens or not word_tokens:
            return 0.0
        shared = excel_tokens & word_tokens
        # Proporción respecto al conjunto más pequeño (el más específico).
        return len(shared) / min(len(excel_tokens), len(word_tokens)) * 100.0

    def _word_activity_for(
        self, ordinal: int, professional_name: str
    ) -> tuple[WordActivity | None, str | None]:
        """Actividad del Word destino para (numeral, profesional).

        En plantillas normales usa ``_by_ordinal``. En plantillas por profesional
        usa el grupo asignado a ese profesional.
        """
        if not self._has_professional_groups:
            return self._by_ordinal.get(ordinal), None
        group_index, warning = self._resolve_group(professional_name)
        return self._groups.get(group_index, {}).get(ordinal), warning

    def get_activity_ordinals(self) -> list[int]:
        return [a.ordinal for a in self._activities]

    def get_ods_number(self) -> str:
        return self._ods_number

    def get_activities_overview(self) -> list[WordActivityOverview]:
        return [
            WordActivityOverview(
                ordinal=a.ordinal, label=a.label, entregable_count=len(a.entregables)
            )
            for a in self._activities
        ]

    def plan_activity_content(
        self, activity: Activity, professional_name: str = ""
    ) -> ActivityInsertResult:
        """Calcula el resultado de insertar ``activity`` sin escribir nada.

        En plantillas por profesional (ODS 17) se resuelve la sección por el
        nombre; el ``plan`` no reclama secciones para no descuadrar la asignación
        real, así que aquí se usa solo para estimar.
        """
        word_activity = self._peek_word_activity(activity.ordinal, professional_name)
        if word_activity is None:
            return self._not_found_result(activity)
        assignments = self._compute_assignments(activity, word_activity)
        return self._build_result(
            activity, assignments, self._label_mismatch_warnings(activity, word_activity)
        )

    def insert_activity_content(
        self,
        activity: Activity,
        target_ordinal: int | None = None,
        professional_name: str = "",
    ) -> ActivityInsertResult:
        manual = target_ordinal is not None
        ordinal = target_ordinal if target_ordinal is not None else activity.ordinal
        word_activity, group_warning = self._word_activity_for(ordinal, professional_name)
        if word_activity is None:
            return self._not_found_result(activity)

        if manual:
            assignments = self._compute_manual_assignments(activity, word_activity)
            warnings: tuple[str, ...] = (
                f"La actividad {activity.ordinal} se insertó manualmente "
                f"en el numeral {ordinal} del Word.",
            )
        else:
            assignments = self._compute_assignments(activity, word_activity)
            warnings = self._label_mismatch_warnings(activity, word_activity)

        if group_warning:
            warnings = (group_warning, *warnings)

        for word_entregable, items in assignments:
            self._writer.fill_entregable(word_entregable, items)
            self._filled.add(id(word_entregable))

        return self._build_result(activity, assignments, warnings)

    def _peek_word_activity(
        self, ordinal: int, professional_name: str
    ) -> WordActivity | None:
        """Actividad destino para el plan, SIN reclamar la sección.

        En plantillas normales usa ``_by_ordinal``. En plantillas por profesional
        estima la sección por similitud de nombre sin fijar la asignación.
        """
        if not self._has_professional_groups:
            return self._by_ordinal.get(ordinal)
        best_group: int | None = None
        best_score = -1.0
        for group_index, name in self._group_names.items():
            score = self._name_similarity(professional_name, name)
            if score > best_score:
                best_score = score
                best_group = group_index
        if best_group is None:
            return None
        return self._groups.get(best_group, {}).get(ordinal)

    def _label_mismatch_warnings(
        self, activity: Activity, word_activity: WordActivity
    ) -> tuple[str, ...]:
        """Advierte cuando el numeral coincide pero el ENUNCIADO es otro.

        Protege contra archivos de otra ODS: mismo numeral, actividad distinta.
        """
        excel_label = activity.identity.normalized_label
        word_label = normalize_text(strip_leading_numeral(word_activity.label))
        if not excel_label or not word_label:
            return ()
        score = float(fuzz.token_sort_ratio(excel_label, word_label))
        if score >= _LABEL_SIMILARITY_THRESHOLD:
            return ()
        return (
            f"El enunciado de la actividad {activity.ordinal} no coincide con el de "
            f"la plantilla (similitud {score:.0f}%). Verifique que el archivo "
            "corresponda a esta ODS.",
        )

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
