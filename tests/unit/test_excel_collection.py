"""Pruebas de la lógica de reunión de archivos Excel."""

from __future__ import annotations

from pathlib import Path

from ods_reporter.presentation.views.components.excel_collection import (
    collect_from_folder,
    merge_unique,
)


def test_collect_from_folder_finds_excels(tmp_path: Path) -> None:
    (tmp_path / "a.xlsx").write_text("x")
    (tmp_path / "b.xlsm").write_text("x")
    (tmp_path / "c.txt").write_text("x")
    (tmp_path / "~$temporal.xlsx").write_text("x")  # temporal de Excel: se ignora
    result = collect_from_folder(tmp_path)
    nombres = sorted(Path(p).name for p in result)
    assert nombres == ["a.xlsx", "b.xlsm"]


def test_collect_from_folder_empty_for_missing(tmp_path: Path) -> None:
    assert collect_from_folder(tmp_path / "no_existe") == []


def test_merge_unique_preserves_order_and_dedupes(tmp_path: Path) -> None:
    a = str(tmp_path / "a.xlsx")
    b = str(tmp_path / "b.xlsx")
    for p in (a, b):
        Path(p).write_text("x")
    merged = merge_unique([a], [b, a])
    assert merged == [a, b]


def test_merge_unique_dedupes_equivalent_paths(tmp_path: Path) -> None:
    (tmp_path / "a.xlsx").write_text("x")
    a1 = str(tmp_path / "a.xlsx")
    a2 = str(tmp_path / "." / "a.xlsx")  # misma ruta, forma distinta
    merged = merge_unique([a1], [a2])
    assert len(merged) == 1
