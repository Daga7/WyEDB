"""Auditoría de profesionales.

Identifica, para el seguimiento que pidió el usuario, los profesionales que no
reportaron actividades y los que reportaron menos del mínimo establecido.
"""

from __future__ import annotations

from collections.abc import Sequence

from ods_reporter.domain.entities.processing_result import ProfessionalAudit
from ods_reporter.domain.entities.professional import Professional
from ods_reporter.shared.constants import MIN_ACTIVITIES_THRESHOLD


class ProfessionalAuditor:
    """Audita la participación de los profesionales en el periodo."""

    def __init__(self, threshold: int = MIN_ACTIVITIES_THRESHOLD) -> None:
        self._threshold = threshold

    def audit(self, professionals: Sequence[Professional]) -> ProfessionalAudit:
        without_activities: list[str] = []
        below_threshold: list[tuple[str, int]] = []

        for professional in professionals:
            count = professional.content_activity_count
            name = professional.name or professional.source_file or "(desconocido)"
            if count == 0:
                without_activities.append(name)
            elif count < self._threshold:
                below_threshold.append((name, count))

        return ProfessionalAudit(
            without_activities=tuple(without_activities),
            below_threshold=tuple(below_threshold),
        )
