"""Selector de archivos de profesionales (Excel o Word) con lista acumulable.

Permite agregar archivos sueltos (de cualquier carpeta) o una carpeta completa,
acumulando la selección, mostrando cada archivo como una fila con su estado y
permitiendo quitar elementos. Pensado para el caso real de 10-30 reportes (uno
por profesional, en Excel .xlsx/.xlsm o Word .docx), en carpetas distintas.
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
    """Lista acumulable de archivos de profesionales a procesar."""

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
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_list()
        self._build_footer_buttons()
        self._refresh()

    # --- Construcción ---

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, pady=(0, 6), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        self._title = ctk.CTkLabel(
            header,
            text="📊  Archivos de profesionales (0)",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self._title.grid(row=0, column=0, sticky="w")

        self._add_files_btn = ctk.CTkButton(
            header,
            text="+  Agregar archivos",
            width=150,
            height=32,
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            command=self._on_add_files,
        )
        self._add_files_btn.grid(row=0, column=1, sticky="e")

    def _build_list(self) -> None:
        self._list = ctk.CTkScrollableFrame(
            self, height=170, fg_color=theme.CARD_INNER, corner_radius=10
        )
        self._list.grid(row=1, column=0, sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)

    def _build_footer_buttons(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, pady=(8, 0), sticky="ew")

        self._add_folder_btn = ctk.CTkButton(
            bar,
            text="📁  Agregar carpeta",
            width=150,
            height=30,
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=self._on_add_folder,
        )
        self._add_folder_btn.pack(side="left", padx=(0, 6))

        self._clear_btn = ctk.CTkButton(
            bar,
            text="🗑  Quitar todo",
            width=120,
            height=30,
            fg_color="transparent",
            border_width=1,
            border_color=theme.BORDER,
            text_color=theme.MUTED,
            hover_color=theme.SECONDARY,
            command=self._on_clear,
        )
        self._clear_btn.pack(side="left")

    # --- Acciones ---

    def _on_add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Selecciona los reportes de los profesionales",
            filetypes=[
                ("Excel o Word de profesionales", "*.xlsx *.xlsm *.docx"),
                ("Libros de Excel", "*.xlsx *.xlsm"),
                ("Documentos Word", "*.docx"),
            ],
        )
        if paths:
            self._files = merge_unique(self._files, list(paths))
            self._refresh()

    def _on_add_folder(self) -> None:
        folder = filedialog.askdirectory(
            title="Selecciona una carpeta con reportes (Excel o Word)"
        )
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
        self._title.configure(text=f"📊  Archivos de profesionales ({len(self._files)})")
        for child in self._list.winfo_children():
            child.destroy()
        self._buttons = []

        if not self._files:
            ctk.CTkLabel(
                self._list,
                text="Sin archivos. Usa «Agregar archivos» o «Agregar carpeta».",
                text_color=theme.MUTED,
            ).grid(row=0, column=0, padx=10, pady=12, sticky="w")
        else:
            for index, path in enumerate(self._files):
                self._render_row(index, path)

        if self._on_change is not None:
            self._on_change(len(self._files))

    def _render_row(self, index: int, path: str) -> None:
        row = ctk.CTkFrame(self._list, fg_color=theme.CARD, corner_radius=8)
        row.grid(row=index, column=0, padx=6, pady=3, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(row, text=Path(path).name, anchor="w").grid(
            row=0, column=0, padx=(10, 4), pady=6, sticky="w"
        )
        kind = "Word" if path.lower().endswith(".docx") else "Excel"
        ctk.CTkLabel(
            row,
            text=f"● {kind}",
            font=ctk.CTkFont(size=11),
            fg_color=theme.SUCCESS_CHIP_BG,
            text_color=theme.SUCCESS_CHIP_TEXT,
            corner_radius=8,
            padx=8,
        ).grid(row=0, column=1, padx=4, pady=6)
        remove_button = ctk.CTkButton(
            row,
            text="✕",
            width=26,
            height=24,
            fg_color="transparent",
            text_color=theme.MUTED,
            hover_color=theme.SECONDARY,
            command=lambda p=path: self._remove(p),
        )
        remove_button.grid(row=0, column=2, padx=(0, 6), pady=4)
        self._buttons.append(remove_button)
