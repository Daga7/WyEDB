"""Pruebas del auditor de profesionales."""

from __future__ import annotations

from ods_reporter.application.services.professional_auditor import ProfessionalAuditor
from ods_reporter.domain.entities.activity import Activity
from ods_reporter.domain.entities.entregable import Entregable
from ods_reporter.domain.entities.professional import Professional
from ods_reporter.domain.value_objects.content_item import ContentItem


def _professional(name: str, n_with_content: int) -> Professional:
    activities = tuple(
        Activity(
            ordinal=i + 1,
            label=f"act {i + 1}",
            entregables=(Entregable("e", (ContentItem("x"),)),),
        )
        for i in range(n_with_content)
    )
    return Professional(name=name, source_file=f"{name}.xlsx", activities=activities)


def test_flags_professional_without_activities() -> None:
    auditor = ProfessionalAuditor(threshold=5)
    audit = auditor.audit([_professional("Sin Datos", 0)])
    assert audit.without_activities == ("Sin Datos",)
    assert audit.below_threshold == ()


def test_flags_professional_below_threshold() -> None:
    auditor = ProfessionalAuditor(threshold=5)
    audit = auditor.audit([_professional("Poco Activa", 3)])
    assert audit.below_threshold == (("Poco Activa", 3),)
    assert audit.without_activities == ()


def test_professional_at_or_above_threshold_not_flagged() -> None:
    auditor = ProfessionalAuditor(threshold=5)
    audit = auditor.audit([_professional("Activa", 5), _professional("Muy Activa", 9)])
    assert audit.without_activities == ()
    assert audit.below_threshold == ()


def test_mixed_professionals() -> None:
    auditor = ProfessionalAuditor(threshold=5)
    audit = auditor.audit(
        [_professional("A", 0), _professional("B", 2), _professional("C", 8)]
    )
    assert audit.without_activities == ("A",)
    assert audit.below_threshold == (("B", 2),)
