"""Entidad ``Professional``: un profesional y las actividades que reportó.

Cada archivo Excel corresponde a un profesional. Esta entidad agrupa sus
actividades y expone las consultas que necesita la auditoría (Fase 9):
profesionales sin actividades y profesionales por debajo del umbral.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ods_reporter.domain.entities.activity import Activity


@dataclass(frozen=True, slots=True)
class Professional:
    """Un profesional con las actividades leídas de su Excel.

    Attributes
    ----------
    name:
        Nombre del profesional responsable (cabecera del Excel).
    source_file:
        Nombre del archivo Excel de origen (para el reporte y el log).
    activities:
        Todas las actividades leídas para el periodo (con o sin contenido).
    """

    name: str
    source_file: str
    activities: tuple[Activity, ...] = field(default_factory=tuple)

    @property
    def activities_with_content(self) -> tuple[Activity, ...]:
        """Actividades que sí fueron diligenciadas (tienen contenido)."""
        return tuple(activity for activity in self.activities if activity.has_content)

    @property
    def content_activity_count(self) -> int:
        """Cantidad de actividades con contenido reportadas por el profesional."""
        return len(self.activities_with_content)

    @property
    def has_no_activities(self) -> bool:
        """``True`` si el profesional no reportó ninguna actividad con contenido."""
        return self.content_activity_count == 0
