"""Capa de dominio: entidades y reglas de negocio puras, sin dependencias externas."""

from ods_reporter.domain.entities.activity import Activity
from ods_reporter.domain.entities.entregable import Entregable
from ods_reporter.domain.entities.ods_metadata import ODSMetadata
from ods_reporter.domain.entities.processing_result import (
    ProcessingResult,
    ProfessionalAudit,
)
from ods_reporter.domain.entities.professional import Professional
from ods_reporter.domain.value_objects.activity_identity import ActivityIdentity
from ods_reporter.domain.value_objects.content_item import ContentItem

__all__ = [
    "Activity",
    "ActivityIdentity",
    "ContentItem",
    "Entregable",
    "ODSMetadata",
    "ProcessingResult",
    "Professional",
    "ProfessionalAudit",
]
