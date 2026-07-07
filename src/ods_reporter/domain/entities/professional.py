"""Entidad ``Professional``: un profesional y las actividades que reportó.

Cada archivo Excel corresponde a un profesional. Esta entidad agrupa sus
actividades y expone las consultas que necesita la auditoría (Fase 9):
profesionales sin actividades y profesionales por debajo del umbral.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ods_reporter.domain.entities.activity import Activity
from ods_reporter.domain.value_objects.content_item import ContentItem


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
    other_activities:
        Actividades adicionales ("otras actividades solicitadas"), ya
        normalizadas y con su fecha incorporada al texto. Se insertan en la
        sección de observaciones del Word.
    ods_number:
        Texto del campo "ODS N°" de la cabecera del Excel (crudo, puede venir
        como "3040727 ECP ODS No. 11"). Se usa para validar que el archivo
        corresponda a la misma ODS de la plantilla Word.
    """

    name: str
    source_file: str
    activities: tuple[Activity, ...] = field(default_factory=tuple)
    other_activities: tuple[ContentItem, ...] = field(default_factory=tuple)
    ods_number: str = ""

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
