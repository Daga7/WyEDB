"""Panel con barra de progreso y etiqueta de estado."""

from __future__ import annotations

import customtkinter as ctk


class ProgressPanel(ctk.CTkFrame):
    """Barra de progreso + texto de estado en tiempo real."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        self._bar = ctk.CTkProgressBar(self)
        self._bar.grid(row=0, column=0, padx=0, pady=(0, 4), sticky="ew")
        self._bar.set(0)

        self._status = ctk.CTkLabel(self, text="Listo.", anchor="w")
        self._status.grid(row=1, column=0, sticky="ew")

    def set_progress(self, current: int, total: int) -> None:
        fraction = current / total if total else 0
        self._bar.set(fraction)
        self._status.configure(text=f"Procesando… {current}/{total}")

    def set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def reset(self) -> None:
        self._bar.set(0)
        self._status.configure(text="Listo.")

    def complete(self) -> None:
        self._bar.set(1)
