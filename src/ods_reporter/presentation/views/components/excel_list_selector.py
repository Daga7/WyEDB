"""Selector de múltiples archivos Excel con lista acumulable.

Permite agregar archivos sueltos (de cualquier carpeta) o una carpeta completa,
acumulando la selección, mostrando la lista y permitiendo quitar elementos. Pensado
para el caso real de 10-30 Excel (uno por profesional), posiblemente en carpetas
distintas.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ods_reporter.presentation import theme
from ods_reporter.presentation.views.components.excel_collection import (
    collect_from_folder,
    merge_unique,
)

ChangeCallback = Callable[[int], None]


class ExcelListSelector(ctk.CTkFrame):
    """Lista acumulable de archivos Excel a procesar."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_change: ChangeCallback | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._files: list[str] = []
        self._on_change = on_change
        self._buttons: list[ctk.CTkButton] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_buttons()
        self._build_list()
        self._refresh()

    # --- Construcción ---

    def _build_header(self) -> None:
        self._title = ctk.CTkLabel(self, text="Archivos Excel (0):", anchor="w")
        self._title.grid(row=0, column=0, pady=(6, 2), sticky="w")

    def _build_buttons(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, pady=2, sticky="ew")

        self._add_files_btn = ctk.CTkButton(
            bar,
            text="Agregar archivos",
            width=146,
            height=30,
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=self._on_add_files,
        )
        self._add_files_btn.pack(side="left", padx=(0, 6))

        self._add_folder_btn = ctk.CTkButton(
            bar,
            text="Agregar carpeta",
            width=146,
            height=30,
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=self._on_add_folder,
        )
        self._add_folder_btn.pack(side="left", padx=(0, 6))

        self._clear_btn = ctk.CTkButton(
            bar,
            text="Quitar todo",
            width=100,
            height=30,
            fg_color="transparent",
            border_width=1,
            border_color=theme.MUTED,
            text_color=theme.MUTED,
            hover_color=("gray92", "gray20"),
            command=self._on_clear,
        )
        self._clear_btn.pack(side="left")

    def _build_list(self) -> None:
        self._list = ctk.CTkScrollableFrame(
            self, height=132, fg_color=theme.CARD_INNER, corner_radius=8
        )
        self._list.grid(row=2, column=0, pady=(4, 6), sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

    # --- Acciones ---

    def _on_add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Selecciona archivos Excel",
            filetypes=[("Libros de Excel", "*.xlsx *.xlsm")],
        )
        if paths:
            self._files = merge_unique(self._files, list(paths))
            self._refresh()

    def _on_add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecciona una carpeta con Excel")
        if folder:
            self._files = merge_unique(self._files, collect_from_folder(folder))
            self._refresh()

    def _on_clear(self) -> None:
        self._files = []
        self._refresh()

    def _remove(self, path: str) -> None:
        self._files = [p for p in self._files if p != path]
        self._refresh()

    # --- Estado / render ---

    def get_files(self) -> tuple[str, ...]:
        return tuple(self._files)

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in (self._add_files_btn, self._add_folder_btn, self._clear_btn):
            button.configure(state=state)
        for remove_button in self._buttons:
            remove_button.configure(state=state)

    def _refresh(self) -> None:
        self._title.configure(text=f"Archivos Excel ({len(self._files)}):")
        for child in self._list.winfo_children():
            child.destroy()
        self._buttons = []

        if not self._files:
            ctk.CTkLabel(
                self._list,
                text="Sin archivos. Usa «Agregar archivos» o «Agregar carpeta».",
                text_color=("gray45", "gray60"),
            ).grid(row=0, column=0, padx=8, pady=8, sticky="w")
        else:
            for index, path in enumerate(self._files):
                self._render_row(index, path)

        if self._on_change is not None:
            self._on_change(len(self._files))

    def _render_row(self, index: int, path: str) -> None:
        row = ctk.CTkFrame(self._list, fg_color="transparent")
        row.grid(row=index, column=0, padx=4, pady=1, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(row, text=Path(path).name, anchor="w").grid(
            row=0, column=0, padx=(8, 4), pady=2, sticky="w"
        )
        remove_button = ctk.CTkButton(
            row,
            text="✕",
            width=26,
            height=24,
            fg_color="transparent",
            text_color=theme.MUTED,
            hover_color=("gray85", "gray25"),
            command=lambda p=path: self._remove(p),
        )
        remove_button.grid(row=0, column=1, padx=(0, 4), pady=1)
        self._buttons.append(remove_button)
