"""Pruebas de las rutas de datos del usuario (fix del error de logs en el .exe)."""

from __future__ import annotations

from pathlib import Path

from ods_reporter.infrastructure.logging.logger_config import setup_logging
from ods_reporter.shared.app_paths import logs_dir, user_data_dir


def test_user_data_dir_is_under_home() -> None:
    # La carpeta de datos cuelga del usuario, nunca del directorio de trabajo.
    data = user_data_dir()
    assert "ODS Reporter" in str(data)


def test_logs_dir_is_writable() -> None:
    directory = logs_dir()
    assert directory.is_dir()
    probe = directory / ".probe"
    probe.write_text("ok", encoding="utf-8")
    assert probe.read_text(encoding="utf-8") == "ok"
    probe.unlink()


def test_setup_logging_uses_explicit_dir(tmp_path: Path) -> None:
    # Con un directorio explícito, escribe ahí (no en el de trabajo).
    log_file = setup_logging(log_dir=tmp_path)
    assert log_file.parent == tmp_path
    assert log_file.exists()
