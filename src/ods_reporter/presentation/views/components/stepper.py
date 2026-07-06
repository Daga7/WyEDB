"""Indicador de pasos del flujo (stepper horizontal).

Muestra los pasos del proceso con su estado: pendiente (círculo gris con
número), en progreso (círculo verde con número) o completado (círculo verde
con visto). Es solo informativo: no captura clics.
"""

from __future__ import annotations

from typing import Literal

import customtkinter as ctk

from ods_reporter.presentation import theme

StepState = Literal["pending", "active", "done"]

_STATE_LABEL: dict[StepState, str] = {
    "pending": "Pendiente",
    "active": "En progreso",
    "done": "Completado",
}


class Stepper(ctk.CTkFrame):
    """Fila de pasos numerados con estado visual."""

    def __init__(self, master: ctk.CTkBaseClass, steps: list[str]) -> None:
        super().__init__(
            master,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER,
        )
        self._circles: list[ctk.CTkLabel] = []
        self._statuses: list[ctk.CTkLabel] = []

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(padx=16, pady=10, anchor="w")

        for index, name in enumerate(steps):
            if index > 0:
                ctk.CTkLabel(inner, text="→", text_color=theme.MUTED).pack(
                    side="left", padx=10
                )

            circle = ctk.CTkLabel(
                inner,
                text=str(index + 1),
                width=30,
                height=30,
                corner_radius=15,
                fg_color=theme.STEP_PENDING_BG,
                text_color=theme.STEP_PENDING_TEXT,
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            circle.pack(side="left")
            self._circles.append(circle)

            texts = ctk.CTkFrame(inner, fg_color="transparent")
            texts.pack(side="left", padx=(8, 0))
            ctk.CTkLabel(
                texts, text=name, font=ctk.CTkFont(size=12, weight="bold"), anchor="w"
            ).pack(anchor="w")
            status = ctk.CTkLabel(
                texts,
                text=_STATE_LABEL["pending"],
                font=ctk.CTkFont(size=10),
                text_color=theme.MUTED,
                anchor="w",
                height=12,
            )
            status.pack(anchor="w")
            self._statuses.append(status)

    def set_states(self, states: list[StepState]) -> None:
        """Actualiza el estado visual de cada paso (misma longitud que los pasos)."""
        for index, state in enumerate(states):
            if index >= len(self._circles):
                break
            circle, status = self._circles[index], self._statuses[index]
            if state == "done":
                circle.configure(text="✓", fg_color=theme.PRIMARY, text_color="white")
            elif state == "active":
                circle.configure(
                    text=str(index + 1), fg_color=theme.PRIMARY, text_color="white"
                )
            else:
                circle.configure(
                    text=str(index + 1),
                    fg_color=theme.STEP_PENDING_BG,
                    text_color=theme.STEP_PENDING_TEXT,
                )
            status.configure(
                text=_STATE_LABEL[state],
                text_color=theme.PRIMARY if state != "pending" else theme.MUTED,
            )
