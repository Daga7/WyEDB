"""Reasignación de numerales por enunciado (modo Word → Word).

En el modo Excel → Word el numeral manda y el comportamiento queda intacto.
Cuando el origen es el Word de un profesional, los numerales pueden variar
entre versiones del documento, así que aquí cada actividad se empareja
principalmente por su **enunciado** (similitud difusa) contra las actividades
de la plantilla, y su numeral se reescribe al de la plantilla ANTES de planear
la inserción. A partir de ahí el flujo (plan, revisión, escritura) es el mismo.

Reglas:

- Cada actividad de la plantilla se asigna a lo sumo una vez (gana la pareja
  de mayor similitud).
- Una actividad de origen sin equivalente por enunciado NUNCA se deja con un
  numeral que exista en la plantilla "por casualidad": se le da un numeral
  sintético para que aparezca como "contenido sin ubicación" y el usuario
  decida su destino en la revisión.
"""

from __future__ import annotations

from dataclasses import replace

from rapidfuzz import fuzz

from ods_reporter.application.ports.word_processor_port import WordActivityOverview
from ods_reporter.domain.entities.professional import Professional
from ods_reporter.shared.text_utils import normalize_text, strip_leading_numeral

# Umbral para aceptar que dos enunciados son la misma actividad. Calibrado con
# datos reales: misma ODS ~100 de similitud; ODS distinta ~29. Queda holgura
# para pequeñas diferencias de redacción sin aceptar actividades ajenas.
LABEL_REMAP_THRESHOLD = 75.0


class ActivityLabelRemapper:
    """Reescribe los numerales de un profesional según el enunciado."""

    def __init__(self, threshold: float = LABEL_REMAP_THRESHOLD) -> None:
        self._threshold = threshold

    def remap(
        self, professional: Professional, overview: list[WordActivityOverview]
    ) -> tuple[Professional, tuple[str, ...]]:
        """Devuelve el profesional con numerales de la plantilla + advertencias."""
        if not overview or not professional.activities:
            return professional, ()

        template_labels = {
            item.ordinal: normalize_text(strip_leading_numeral(item.label))
            for item in overview
        }
        template_ordinals = set(template_labels)

        assignments, scores = self._best_assignments(professional, template_labels)

        synthetic = max(
            template_ordinals | {a.ordinal for a in professional.activities}, default=0
        )
        warnings: list[str] = []
        remapped = []
        for index, activity in enumerate(professional.activities):
            target = assignments.get(index)
            if target is not None:
                if target != activity.ordinal:
                    if activity.has_content:
                        warnings.append(
                            f"La actividad {activity.ordinal} «{_short(activity.label)}» "
                            f"se emparejó por su enunciado con la actividad {target} "
                            f"de la plantilla (similitud {scores[index]:.0f}%)."
                        )
                    activity = replace(activity, ordinal=target)
                remapped.append(activity)
                continue

            if activity.ordinal in template_ordinals:
                synthetic += 1
                if activity.has_content:
                    warnings.append(
                        f"La actividad «{_short(activity.label)}» no coincide con "
                        "ninguna de la plantilla: revísala en «contenido sin "
                        "ubicación»."
                    )
                activity = replace(activity, ordinal=synthetic)
            remapped.append(activity)

        return replace(professional, activities=tuple(remapped)), tuple(warnings)

    def _best_assignments(
        self, professional: Professional, template_labels: dict[int, str]
    ) -> tuple[dict[int, int], dict[int, float]]:
        """Asigna origen → plantilla por mayor similitud, sin repetir destinos."""
        pairs: list[tuple[float, int, int]] = []
        for index, activity in enumerate(professional.activities):
            source_label = activity.identity.normalized_label
            if not source_label:
                continue
            for ordinal, label in template_labels.items():
                if not label:
                    continue
                score = float(fuzz.token_sort_ratio(source_label, label))
                if score >= self._threshold:
                    pairs.append((score, index, ordinal))

        pairs.sort(key=lambda pair: pair[0], reverse=True)
        assignments: dict[int, int] = {}
        scores: dict[int, float] = {}
        used: set[int] = set()
        for score, index, ordinal in pairs:
            if index in assignments or ordinal in used:
                continue
            assignments[index] = ordinal
            used.add(ordinal)
            scores[index] = score
        return assignments, scores


def _short(text: str, max_len: int = 48) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= max_len else cleaned[: max_len - 1] + "…"
