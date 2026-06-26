"""Pruebas del alineador de entregables."""

from __future__ import annotations

from ods_reporter.application.services.entregable_aligner import EntregableAligner


def test_aligns_identical_texts() -> None:
    aligner = EntregableAligner()
    source = ["Cargar en repositorio de información", "Plan de Acción actualizado"]
    target = ["Plan de Acción actualizado", "Cargar en repositorio de información"]
    # El orden de los objetivos está invertido; la alineación lo resuelve por texto.
    assert aligner.align(source, target) == [1, 0]


def test_aligns_one_to_one() -> None:
    aligner = EntregableAligner()
    source = ["Cargar soporte documental", "Cargar soporte documental"]
    target = ["Cargar soporte documental", "Otro entregable distinto"]
    result = aligner.align(source, target)
    # No se reutiliza el mismo objetivo: el segundo cae en el leftover (índice 1).
    assert result[0] == 0
    assert result[1] == 1


def test_unmatched_returns_none() -> None:
    aligner = EntregableAligner()
    source = ["Texto totalmente diferente aaa", "Otro sin relación bbb"]
    target = ["Cargar en repositorio de información soporte documental ICA ANLA"]
    result = aligner.align(source, target)
    assert result.count(None) >= 1


def test_single_leftover_assigned_positionally() -> None:
    aligner = EntregableAligner(threshold=95.0)
    # El texto difiere lo suficiente para no superar el umbral alto,
    # pero al quedar un único objetivo y un único origen libres, se asigna.
    source = ["Plan de accion v2 modificado"]
    target = ["Plan de Acción actualizado en el formato"]
    result = aligner.align(source, target)
    assert result == [0]


def test_empty_inputs() -> None:
    aligner = EntregableAligner()
    assert aligner.align([], []) == []
    assert aligner.align(["algo"], []) == [None]
