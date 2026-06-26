"""Pruebas de la lógica de reparto de contenido por entregable (match_each).

Verifica la regla pedida por el usuario:
  - Si el Excel está DIVIDIDO por entregable -> cada contenido a su sub-fila.
  - Si NO está dividido (un solo bloque) -> ese contenido va a TODAS las sub-filas.
La lógica de replicación vive en el procesador; aquí se prueba el emparejamiento
no exclusivo del alineador, que es su base.
"""

from __future__ import annotations

from ods_reporter.application.services.entregable_aligner import EntregableAligner


def test_match_each_divided() -> None:
    aligner = EntregableAligner()
    # Dos sub-filas del Word, dos entregables del Excel con textos distintos.
    word = ["matriz de requisitos legales actualizada", "plan de accion elaborado"]
    excel = ["plan de accion elaborado", "matriz de requisitos legales actualizada"]
    # Cada sub-fila trae su entregable correspondiente (no posicional, por texto).
    assert aligner.match_each(word, excel) == [1, 0]


def test_match_each_allows_repeated_source() -> None:
    aligner = EntregableAligner()
    # Una sola fuente puede ser la mejor de varias sub-filas (no es exclusivo).
    word = ["plan de accion elaborado", "plan de accion elaborado v2"]
    excel = ["plan de accion elaborado"]
    assert aligner.match_each(word, excel) == [0, 0]


def test_match_each_no_match_returns_none() -> None:
    aligner = EntregableAligner()
    word = ["texto completamente distinto aaa"]
    excel = ["otra cosa sin relacion bbb"]
    assert aligner.match_each(word, excel) == [None]
