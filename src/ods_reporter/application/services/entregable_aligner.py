"""Alineador de entregables entre el Excel y el Word.

Dentro de una misma actividad, empareja cada entregable del Excel con su
entregable correspondiente del Word **por similitud de texto** (como confirmó el
usuario). Trabaja con cadenas e índices —sin conocer el dominio ni el Word— para
mantenerse desacoplado y fácil de probar.

Emparejamiento uno a uno (cada entregable del Word se usa una sola vez), de forma
voraz por la mejor similitud. Los entregables del Excel sin coincidencia clara
quedan sin alinear (``None``); la capa superior decide qué hacer con ellos.
"""

from __future__ import annotations

from collections.abc import Sequence

from rapidfuzz import fuzz

# Umbral de similitud para aceptar la alineación de un entregable (0-100).
# Los entregables suelen ser casi idénticos entre Excel y Word, por lo que un
# umbral moderado evita falsos negativos sin emparejar textos no relacionados.
DEFAULT_THRESHOLD = 75.0


class EntregableAligner:
    """Alinea entregables del Excel con los del Word por similitud de texto."""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        self._threshold = threshold

    def align(
        self,
        source_texts: Sequence[str],
        target_texts: Sequence[str],
    ) -> list[int | None]:
        """Para cada texto de ``source_texts`` devuelve el índice del mejor
        ``target_texts`` (uno a uno) o ``None`` si no supera el umbral.

        Si solo queda un objetivo libre y un origen sin emparejar, se asigna por
        descarte (alineación posicional de respaldo), para no perder contenido
        cuando los textos difieren pero la correspondencia es evidente.
        """
        used: set[int] = set()
        result: list[int | None] = []

        for source in source_texts:
            best_index: int | None = None
            best_score = -1.0
            for index, target in enumerate(target_texts):
                if index in used:
                    continue
                score = float(fuzz.token_sort_ratio(source, target))
                if score > best_score:
                    best_score = score
                    best_index = index
            if best_index is not None and best_score >= self._threshold:
                used.add(best_index)
                result.append(best_index)
            else:
                result.append(None)

        self._fill_single_leftover(result, len(target_texts), used)
        return result

    @staticmethod
    def _fill_single_leftover(
        result: list[int | None], target_count: int, used: set[int]
    ) -> None:
        """Si queda exactamente un origen sin emparejar y un objetivo libre, los une."""
        free_targets = [i for i in range(target_count) if i not in used]
        missing_positions = [i for i, value in enumerate(result) if value is None]
        if len(free_targets) == 1 and len(missing_positions) == 1:
            result[missing_positions[0]] = free_targets[0]
