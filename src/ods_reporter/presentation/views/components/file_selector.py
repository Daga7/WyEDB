"""Fila de selección de archivo/carpeta reutilizable.

Muestra una etiqueta, un campo de solo lectura con la selección actual y un botón
"Examinar". El tipo de diálogo (archivo, varios archivos o carpeta) se configura.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

BrowseCallback = Callable[[], None]


class FileSelector(ctk.CTkFrame):
    """Selector genérico con etiqueta, valor y botón Examinar."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        label: str,
        on_browse: BrowseCallback,
        placeholder: str = "Sin selección",
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)

        self._label = ctk.CTkLabel(self, text=label, width=160, anchor="w")
        self._label.grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")

        self._value = ctk.CTkLabel(
            self,
            text=placeholder,
            anchor="w",
            fg_color=("gray90", "gray20"),
            corner_radius=6,
            padx=10,
        )
        self._value.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="ew")

        self._button = ctk.CTkButton(self, text="Examinar", width=110, command=on_browse)
        self._button.grid(row=0, column=2, pady=4)

        self._placeholder = placeholder

    def set_value(self, text: str) -> None:
        self._value.configure(text=text or self._placeholder)

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._button.configure(state=state)
