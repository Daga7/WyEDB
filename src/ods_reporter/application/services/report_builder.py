"""Ensamblador del dominio a partir del reporte crudo del Excel.

Toma un ``RawReport`` (extracción fiel del lector) y produce un ``Professional``
del dominio, con sus actividades y el contenido ya normalizado. Es el puente
entre la capa de infraestructura (lectura) y el dominio.
"""

from __future__ import annotations

from ods_reporter.application.ports.excel_reader_port import RawActivity, RawReport
from ods_reporter.application.services.content_normalizer import ContentNormalizer
from ods_reporter.domain.entities.activity import Activity
from ods_reporter.domain.entities.entregable import Entregable
from ods_reporter.domain.entities.professional import Professional


class ReportBuilder:
    """Construye un ``Professional`` del dominio desde un ``RawReport``."""

    def __init__(self, normalizer: ContentNormalizer | None = None) -> None:
        self._normalizer = normalizer or ContentNormalizer()

    def build(self, raw_report: RawReport) -> Professional:
        activities = tuple(self._build_activity(raw) for raw in raw_report.activities)
        return Professional(
            name=raw_report.professional_name,
            source_file=raw_report.source_file,
            activities=activities,
        )

    def _build_activity(self, raw_activity: RawActivity) -> Activity:
        entregables = tuple(
            Entregable(
                entregable_text=raw_entregable.entregable_text,
                content_items=self._normalizer.normalize((raw_entregable.raw_content,)),
            )
            for raw_entregable in raw_activity.entregables
        )
        return Activity(
            ordinal=raw_activity.ordinal,
            label=raw_activity.label,
            entregables=entregables,
        )
