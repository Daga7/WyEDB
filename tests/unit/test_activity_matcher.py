"""Pruebas del emparejador de actividades."""

from __future__ import annotations

import pytest

from ods_reporter.application.services.activity_matcher import ActivityMatcher
from ods_reporter.domain.value_objects.activity_identity import ActivityIdentity


def _id(ordinal: int, label: str) -> ActivityIdentity:
    return ActivityIdentity(ordinal=ordinal, normalized_label=label)


@pytest.fixture
def candidates() -> list[ActivityIdentity]:
    return [
        _id(1, "identificar y analizar plan de accion"),
        _id(2, "elaborar el recurso de reposicion"),
        _id(3, "identificar y analizar plan de accion"),  # mismo texto, distinto numeral
        _id(4, "implementar hacer seguimiento consolidar soportes"),
    ]


def test_matches_by_ordinal_and_text(candidates: list[ActivityIdentity]) -> None:
    matcher = ActivityMatcher(candidates)
    result = matcher.match(_id(2, "elaborar el recurso de reposicion"))
    assert result is not None
    assert result.identity.ordinal == 2
    assert result.method == "numeral+texto"
    assert result.score == pytest.approx(100.0)


def test_same_text_different_numeral_uses_numeral(candidates: list[ActivityIdentity]) -> None:
    # Texto idéntico en numeral 1 y 3; el numeral decide.
    result = ActivityMatcher(candidates).match(_id(3, "identificar y analizar plan de accion"))
    assert result is not None
    assert result.identity.ordinal == 3


def test_ordinal_match_with_divergent_text_still_matches(
    candidates: list[ActivityIdentity],
) -> None:
    # El numeral manda aunque el texto difiera; se marca como "numeral" (dudoso).
    result = ActivityMatcher(candidates).match(_id(4, "texto totalmente diferente xyz"))
    assert result is not None
    assert result.identity.ordinal == 4
    assert result.method == "numeral"


def test_fuzzy_fallback_when_ordinal_absent(candidates: list[ActivityIdentity]) -> None:
    # Numeral 99 no existe; debe emparejar por texto con la actividad 4.
    result = ActivityMatcher(candidates).match(
        _id(99, "implementar hacer seguimiento consolidar soportes")
    )
    assert result is not None
    assert result.identity.ordinal == 4
    assert result.method == "texto"


def test_no_match_when_text_too_different(candidates: list[ActivityIdentity]) -> None:
    result = ActivityMatcher(candidates).match(_id(99, "contenido sin relacion alguna zzz"))
    assert result is None


def test_empty_candidates_returns_none() -> None:
    assert ActivityMatcher([]).match(_id(1, "algo")) is None
