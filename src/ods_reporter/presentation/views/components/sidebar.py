"""Barra lateral de navegación con el logo de la empresa y los módulos.

Tres módulos: "Nuevo informe", "Resumen detallado" y "Cómo usar" (el manual).
El seleccionado se resalta con el verde corporativo; la vista principal decide
qué hacer al cambiar.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ods_reporter.presentation import branding, theme
from ods_reporter.shared.constants import APP_NAME, APP_VERSION

SelectCallback = Callable[[str], None]

NEW_REPORT = "nuevo"
REVIEW = "resumen"
HELP = "uso"


class Sidebar(ctk.CTkFrame):
    """Navegación lateral fija."""

    def __init__(self, master: ctk.CTkBaseClass, on_select: SelectCallback) -> None:
        super().__init__(master, width=240, corner_radius=0, fg_color=theme.SIDEBAR)
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._on_select = on_select
        self._buttons: dict[str, ctk.CTkButton] = {}

        self._build_brand()
        self._build_nav()
        self._build_decoration()
        self._build_footer()
        self.select(NEW_REPORT, notify=False)

    # --- Construcción ---

    def _build_brand(self) -> None:
        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=0, padx=18, pady=(22, 6), sticky="ew")

        self._logo_image = branding.load_logo(height=52)
        if self._logo_image is not None:
            ctk.CTkLabel(brand, image=self._logo_image, text="").pack(anchor="w")
        else:
            ctk.CTkLabel(
                brand, text=APP_NAME, font=ctk.CTkFont(size=18, weight="bold")
            ).pack(anchor="w")
        ctk.CTkLabel(
            brand,
            text=f"{APP_NAME} · v{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=theme.MUTED,
        ).pack(anchor="w", pady=(6, 0))

    def _build_nav(self) -> None:
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=1, column=0, padx=12, pady=(16, 0), sticky="ew")
        nav.grid_columnconfigure(0, weight=1)

        self._buttons[NEW_REPORT] = self._nav_button(nav, "📝  Nuevo informe", NEW_REPORT, 0)
        self._buttons[REVIEW] = self._nav_button(nav, "📊  Resumen detallado", REVIEW, 1)
        self._buttons[HELP] = self._nav_button(nav, "📖  Cómo usar", HELP, 2)

    def _nav_button(
        self, parent: ctk.CTkFrame, text: str, key: str, row: int
    ) -> ctk.CTkButton:
        button = ctk.CTkButton(
            parent,
            text=text,
            height=42,
            corner_radius=10,
            anchor="w",
            fg_color="transparent",
            text_color=theme.TEXT,
            hover_color=theme.SECONDARY,
            font=ctk.CTkFont(size=13),
            command=lambda: self.select(key),
        )
        button.grid(row=row, column=0, pady=3, sticky="ew")
        return button

    def _build_decoration(self) -> None:
        """Ilustración inferior de la barra lateral (si el recurso existe)."""
        self._decoration = branding.load_decoration("side_left.png", width=212)
        if self._decoration is None:
            return
        ctk.CTkLabel(self, image=self._decoration, text="").grid(
            row=3, column=0, padx=14, pady=(12, 0), sticky="s"
        )

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(
            self,
            fg_color=theme.CARD_INNER,
            corner_radius=12,
        )
        footer.grid(row=4, column=0, padx=14, pady=16, sticky="ew")
        ctk.CTkLabel(
            footer,
            text="🌿 Comprometidos con\nel medio ambiente",
            font=ctk.CTkFont(size=11),
            text_color=theme.MUTED,
            justify="left",
        ).pack(padx=12, pady=10, anchor="w")

    # --- Selección ---

    def select(self, key: str, *, notify: bool = True) -> None:
        for name, button in self._buttons.items():
            if name == key:
                button.configure(
                    fg_color=theme.PRIMARY, text_color="white", hover_color=theme.PRIMARY_HOVER
                )
            else:
                button.configure(
                    fg_color="transparent",
                    text_color=theme.TEXT,
                    hover_color=theme.SECONDARY,
                )
        if notify:
            self._on_select(key)
