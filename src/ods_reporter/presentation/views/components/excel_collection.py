"""Lógica pura para reunir archivos de profesionales (Excel o Word).

Se separa de la interfaz para poder probarla sin abrir ventanas.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ods_reporter.shared.constants import PROFESSIONAL_FILE_EXTENSIONS


def collect_from_folder(folder: str | Path) -> list[str]:
    """Devuelve, ordenados, los reportes (.xlsx/.xlsm/.docx) dentro de ``folder``.

    Ignora archivos temporales de Office (los que empiezan por ``~$``).
    """
    base = Path(folder)
    if not base.is_dir():
        return []
    found = [
        str(path)
        for path in sorted(base.iterdir())
        if path.is_file()
        and path.suffix.lower() in PROFESSIONAL_FILE_EXTENSIONS
        and not path.name.startswith("~$")
    ]
    return found


def merge_unique(existing: Iterable[str], new: Iterable[str]) -> list[str]:
    """Une dos listas de rutas conservando el orden y sin duplicados.

    La comparación usa la ruta absoluta resuelta, de modo que distintas formas de
    la misma ruta no se dupliquen.
    """
    result: list[str] = []
    seen: set[str] = set()
    for path in [*existing, *new]:
        key = _canonical(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def _canonical(path: str) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return path
