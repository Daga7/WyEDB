"""Arranque de la interfaz gráfica."""

from __future__ import annotations

import logging

import customtkinter as ctk

from ods_reporter.presentation.view_models.main_view_model import MainViewModel
from ods_reporter.presentation.views.main_window import MainWindow
from ods_reporter.shared.di_container import build_use_case

logger = logging.getLogger(__name__)


def run_app() -> int:
    """Configura el tema, crea la ventana y entra en el bucle de eventos."""
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    view_model = MainViewModel(use_case_factory=build_use_case)
    window = MainWindow(view_model)
    logger.info("Interfaz iniciada.")
    window.mainloop()
    return 0
