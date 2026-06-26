"""Punto de entrada de la aplicación ODS Reporter.

En esta Fase 2 el ``main`` únicamente arranca el entorno (logging) y verifica que
la base del proyecto es funcional. En la Fase 10 lanzará la interfaz gráfica.
"""

from __future__ import annotations

import logging
import sys

from ods_reporter.infrastructure.logging.logger_config import setup_logging
from ods_reporter.shared.constants import APP_NAME, APP_VERSION


def main() -> int:
    """Arranca la aplicación. Devuelve el código de salida del proceso."""
    log_file = setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Iniciando %s v%s", APP_NAME, APP_VERSION)
    logger.info("Registro de eventos en: %s", log_file)

    try:
        from ods_reporter.presentation.app import run_app
    except ImportError as exc:
        logger.error(
            "No se pudo cargar la interfaz gráfica (¿falta el paquete del sistema "
            "'tk'? Instálalo con 'sudo pacman -S tk'): %s",
            exc,
        )
        return 1

    return run_app()


if __name__ == "__main__":
    sys.exit(main())
