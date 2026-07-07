"""Validador de compatibilidad entre un Excel y la plantilla Word de la ODS.

Evita el error de procesar un informe que pertenece a OTRA ODS. Combina dos
criterios, del más determinante al de respaldo:

  1. **Número de ODS**: si el Excel y el Word declaran números distintos, el
     archivo se rechaza. Es un criterio "mejor esfuerzo": solo aplica cuando
     ambos documentos traen un número reconocible.
  2. **Enunciados de las actividades**: se compara, numeral a numeral, la
     similitud difusa del enunciado del Excel contra el de la plantilla. En la
     misma ODS los enunciados son casi idénticos (~100 de similitud, medido con
     datos reales); en una ODS distinta rondan ~29. Si menos de la mitad de las
     actividades comparables coincide, el archivo se rechaza.

El umbral por actividad (60) y la fracción mínima (0.5) dejan un margen amplio
frente a diferencias menores de redacción, tildes o numeración.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from rapidfuzz import fuzz

from ods_reporter.application.ports.word_processor_port import WordActivityOverview
from ods_reporter.domain.entities.professional import Professional
from ods_reporter.shared.text_utils import (
    extract_ods_number,
    normalize_text,
    strip_leading_numeral,
)

# Similitud mínima (0-100) para considerar que dos enunciados son la misma actividad.
LABEL_SIMILARITY_THRESHOLD = 60.0
# Mínimo de actividades comparables para poder emitir un veredicto por enunciados.
MIN_COMPARABLE_ACTIVITIES = 3
# Fracción mínima de enunciados coincidentes; por debajo, el archivo es de otra ODS.
MIN_MATCH_FRACTION = 0.5


@dataclass(frozen=True, slots=True)
class CompatibilityResult:
    """Veredicto de compatibilidad de un archivo con la plantilla."""

    compatible: bool
    reason: str = ""


class OdsCompatibilityValidator:
    """Decide si el Excel de un profesional corresponde a la ODS de la plantilla."""

    def validate(
        self,
        professional: Professional,
        word_activities: Sequence[WordActivityOverview],
        word_ods_number: str,
    ) -> CompatibilityResult:
        by_number = self._check_ods_numbers(professional.ods_number, word_ods_number)
        if by_number is not None:
            return by_number
        return self._check_labels(professional, word_activities)

    # --- Criterio 1: número de ODS ---

    @staticmethod
    def _check_ods_numbers(
        excel_raw: str, word_raw: str
    ) -> CompatibilityResult | None:
        excel_number = extract_ods_number(excel_raw)
        word_number = extract_ods_number(word_raw)
        if excel_number and word_number and excel_number != word_number:
            return CompatibilityResult(
                compatible=False,
                reason=(
                    f"el Excel declara la ODS {excel_number} y la plantilla "
                    f"Word la ODS {word_number}"
                ),
            )
        return None  # sin veredicto: decide el criterio de enunciados

    # --- Criterio 2: enunciados de las actividades ---

    @staticmethod
    def _check_labels(
        professional: Professional,
        word_activities: Sequence[WordActivityOverview],
    ) -> CompatibilityResult:
        word_labels = {
            overview.ordinal: normalize_text(strip_leading_numeral(overview.label))
            for overview in word_activities
        }
        comparable = 0
        matching = 0
        for activity in professional.activities:
            excel_label = activity.identity.normalized_label
            word_label = word_labels.get(activity.ordinal, "")
            if not excel_label or not word_label:
                continue
            comparable += 1
            score = float(fuzz.token_sort_ratio(excel_label, word_label))
            if score >= LABEL_SIMILARITY_THRESHOLD:
                matching += 1

        if comparable < MIN_COMPARABLE_ACTIVITIES:
            return CompatibilityResult(compatible=True)  # sin señal suficiente

        if matching / comparable < MIN_MATCH_FRACTION:
            return CompatibilityResult(
                compatible=False,
                reason=(
                    f"los enunciados de las actividades no coinciden con la "
                    f"plantilla (solo {matching} de {comparable})"
                ),
            )
        return CompatibilityResult(compatible=True)
