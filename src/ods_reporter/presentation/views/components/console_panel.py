"""Consola de eventos: muestra los mensajes del proceso con color por severidad."""

from __future__ import annotations

import customtkinter as ctk

from ods_reporter.application.ports.progress_port import EventLevel
from ods_reporter.presentation import theme

# Color del texto según la severidad del evento.
_LEVEL_COLORS: dict[EventLevel, str] = {
    EventLevel.INFO: "#dce3ea",
    EventLevel.SUCCESS: "#5cb85c",
    EventLevel.WARNING: "#f0ad4e",
    EventLevel.ERROR: "#d9534f",
}

_LEVEL_PREFIX: dict[EventLevel, str] = {
    EventLevel.INFO: "•",
    EventLevel.SUCCESS: "✔",
    EventLevel.WARNING: "⚠",
    EventLevel.ERROR: "✖",
}


class ConsolePanel(ctk.CTkFrame):
    """Área de texto de solo lectura con los eventos del procesamiento."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text="ACTIVIDAD DEL PROCESO",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=theme.MUTED,
            anchor="w",
        )
        header.grid(row=0, column=0, pady=(4, 4), sticky="w")

        # Fondo oscuro fijo: los colores por severidad se leen igual en ambos temas.
        self._textbox = ctk.CTkTextbox(
            self,
            wrap="word",
            font=("monospace", 12),
            fg_color=theme.CONSOLE_BG,
            corner_radius=8,
        )
        self._textbox.grid(row=1, column=0, pady=(0, 4), sticky="nsew")
        self._textbox.configure(state="disabled")

        # Un tag de color por cada nivel.
        for level, color in _LEVEL_COLORS.items():
            self._textbox.tag_config(level.value, foreground=color)

    def append(self, level: EventLevel, text: str) -> None:
        prefix = _LEVEL_PREFIX.get(level, "•")
        self._textbox.configure(state="normal")
        self._textbox.insert("end", f"{prefix} {text}\n", level.value)
        self._textbox.see("end")
        self._textbox.configure(state="disabled")

    def clear(self) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
