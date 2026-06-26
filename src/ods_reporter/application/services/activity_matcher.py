"""Emparejador de actividades entre el Excel y el Word.

Estrategia (el **numeral manda**, el texto es respaldo):

  1. Si existe una actividad del Word con el mismo numeral, esa es la coincidencia
     (resuelve el caso de textos iguales con numeral distinto). Se calcula además
     la similitud de texto para poder advertir si difieren mucho.
  2. Si no hay ninguna con ese numeral, se busca por **similitud de texto** y se
     acepta solo si supera un umbral alto.

Usa ``rapidfuzz`` para la similitud. Es una librería de algoritmo puro (sin E/S),
por lo que se considera una utilidad y no un detalle de infraestructura con estado.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from ods_reporter.domain.value_objects.activity_identity import ActivityIdentity


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Resultado de un emparejamiento.

    Attributes
    ----------
    identity:
        Identidad de la actividad del Word con la que se emparejó.
    score:
        Similitud de texto (0-100) entre la actividad buscada y la emparejada.
    method:
        Cómo se emparejó: ``"numeral"``, ``"numeral+texto"`` o ``"texto"``.
    """

    identity: ActivityIdentity
    score: float
    method: str


# Umbral por defecto para aceptar un emparejamiento por texto (0-100).
DEFAULT_FUZZY_THRESHOLD = 85.0
# Umbral por debajo del cual una coincidencia por numeral se marca como dudosa.
LOW_TEXT_SCORE = 60.0


class ActivityMatcher:
    """Empareja la identidad de una actividad contra un conjunto de candidatas."""

    def __init__(
        self,
        candidates: Sequence[ActivityIdentity],
        *,
        fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
    ) -> None:
        self._candidates: list[ActivityIdentity] = list(candidates)
        self._threshold = fuzzy_threshold
        self._by_ordinal: dict[int, list[ActivityIdentity]] = {}
        for candidate in self._candidates:
            self._by_ordinal.setdefault(candidate.ordinal, []).append(candidate)

    def match(self, target: ActivityIdentity) -> MatchResult | None:
        """Devuelve la mejor coincidencia para ``target`` o ``None`` si no hay."""
        same_ordinal = self._by_ordinal.get(target.ordinal, [])

        if len(same_ordinal) == 1:
            return self._build_ordinal_result(target, same_ordinal[0])

        if len(same_ordinal) > 1:
            best = max(
                same_ordinal,
                key=lambda c: self._similarity(target.normalized_label, c.normalized_label),
            )
            return self._build_ordinal_result(target, best)

        return self._match_by_text(target)

    # --- Internos ---

    def _build_ordinal_result(
        self, target: ActivityIdentity, candidate: ActivityIdentity
    ) -> MatchResult:
        score = self._similarity(target.normalized_label, candidate.normalized_label)
        method = "numeral+texto" if score >= LOW_TEXT_SCORE else "numeral"
        return MatchResult(identity=candidate, score=score, method=method)

    def _match_by_text(self, target: ActivityIdentity) -> MatchResult | None:
        if not self._candidates:
            return None
        choices = {idx: c.normalized_label for idx, c in enumerate(self._candidates)}
        result = process.extractOne(
            target.normalized_label, choices, scorer=fuzz.token_sort_ratio
        )
        if result is None:
            return None
        _label, score, index = result
        if score < self._threshold:
            return None
        return MatchResult(identity=self._candidates[index], score=score, method="texto")

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        return float(fuzz.token_sort_ratio(a, b))
