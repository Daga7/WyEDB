"""Módulo "Nuevo informe": carga de archivos, configuración y procesamiento.

Columna principal con tarjetas (plantilla Word, archivos de profesionales,
progreso con consola) y carril derecho con el resumen del proceso, el estado
actual y el botón de acción principal. La ventana principal inyecta los
callbacks y consume el estado de los campos.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ods_reporter.application.ports.progress_port import EventLevel
from ods_reporter.presentation import branding, theme
from ods_reporter.presentation.views.components.console_panel import ConsolePanel
from ods_reporter.presentation.views.components.excel_list_selector import ExcelListSelector
from ods_reporter.presentation.views.components.progress_panel import ProgressPanel

Callback = Callable[[], None]


def _card(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=theme.CARD,
        corner_radius=12,
        border_width=1,
        border_color=theme.BORDER,
    )


def _section_title(parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent, text=text, font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
    )


class NewReportView(ctk.CTkFrame):
    """Vista de carga y procesamiento (módulo 1)."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        months: tuple[str, ...],
        on_browse_word: Callback,
        on_browse_output: Callback,
        on_process: Callback,
        on_cancel: Callback,
        on_inputs_changed: Callback,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_inputs_changed = on_inputs_changed
        # Durante la construcción los widgets disparan sus callbacks iniciales;
        # solo se notifica a la ventana cuando la vista está completa.
        self._ready = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Columna principal ---
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)

        self._build_template_card(main, on_browse_word)
        self._build_excel_card(main)
        self._build_config_row(main, months, on_browse_output)
        self._build_progress_card(main, on_cancel)

        # --- Carril derecho ---
        rail = ctk.CTkFrame(self, fg_color="transparent", width=270)
        rail.grid(row=0, column=1, sticky="ns", padx=(14, 0))
        rail.grid_propagate(False)
        rail.grid_columnconfigure(0, weight=1)
        rail.grid_rowconfigure(2, weight=1)
        self._build_summary_card(rail)
        self._build_state_card(rail)
        self._build_rail_decoration(rail)
        self._build_cta(rail, on_process)
        self._ready = True

    def _build_rail_decoration(self, rail: ctk.CTkFrame) -> None:
        """Ilustración del carril derecho (si el recurso existe)."""
        self._decoration = branding.load_decoration("side_right.png", width=252)
        if self._decoration is None:
            return
        ctk.CTkLabel(rail, image=self._decoration, text="").grid(
            row=2, column=0, pady=(12, 0), sticky="s"
        )

    def _notify_inputs_changed(self) -> None:
        if self._ready:
            self._on_inputs_changed()

    # --- Tarjetas de la columna principal ---

    def _build_template_card(self, parent: ctk.CTkFrame, on_browse: Callback) -> None:
        card = _card(parent)
        card.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        _section_title(card, "📄  Plantilla Word seleccionada").grid(
            row=0, column=0, padx=16, pady=(12, 6), sticky="w"
        )

        chip = ctk.CTkFrame(card, fg_color=theme.CARD_INNER, corner_radius=10)
        chip.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="ew")
        chip.grid_columnconfigure(0, weight=1)
        self._template_label = ctk.CTkLabel(
            chip, text="Sin selección", anchor="w", text_color=theme.MUTED
        )
        self._template_label.grid(row=0, column=0, padx=12, pady=10, sticky="ew")
        self._template_button = ctk.CTkButton(
            chip,
            text="✏  Cambiar",
            width=110,
            height=30,
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=on_browse,
        )
        self._template_button.grid(row=0, column=1, padx=(0, 10), pady=8)

    def _build_excel_card(self, parent: ctk.CTkFrame) -> None:
        card = _card(parent)
        card.grid(row=1, column=0, pady=(0, 10), sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        self.excel_selector = ExcelListSelector(
            card, on_change=lambda _count: self._notify_inputs_changed()
        )
        self.excel_selector.grid(row=0, column=0, padx=16, pady=12, sticky="ew")

    def _build_config_row(
        self, parent: ctk.CTkFrame, months: tuple[str, ...], on_browse_output: Callback
    ) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=2, column=0, pady=(0, 10), sticky="ew")
        row.grid_columnconfigure(0, weight=3)
        row.grid_columnconfigure(1, weight=2)

        # Carpeta de salida
        out_card = _card(row)
        out_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        out_card.grid_columnconfigure(0, weight=1)
        _section_title(out_card, "📁  Carpeta de salida").grid(
            row=0, column=0, padx=16, pady=(12, 6), sticky="w"
        )
        chip = ctk.CTkFrame(out_card, fg_color=theme.CARD_INNER, corner_radius=10)
        chip.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="ew")
        chip.grid_columnconfigure(0, weight=1)
        self._output_label = ctk.CTkLabel(
            chip, text="Sin selección", anchor="w", text_color=theme.MUTED
        )
        self._output_label.grid(row=0, column=0, padx=12, pady=8, sticky="ew")
        self._output_button = ctk.CTkButton(
            chip,
            text="Examinar",
            width=100,
            height=28,
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=on_browse_output,
        )
        self._output_button.grid(row=0, column=1, padx=(0, 8), pady=6)

        # Mes a procesar
        month_card = _card(row)
        month_card.grid(row=0, column=1, sticky="nsew")
        month_card.grid_columnconfigure(0, weight=1)
        _section_title(month_card, "🗓  Mes a procesar").grid(
            row=0, column=0, padx=16, pady=(12, 6), sticky="w"
        )
        self.month_var = ctk.StringVar(value="")
        self.month_var.trace_add("write", lambda *_: self._notify_inputs_changed())
        self._month_menu = ctk.CTkOptionMenu(
            month_card,
            values=list(months),
            variable=self.month_var,
            width=180,
            height=32,
            fg_color=theme.CARD_INNER,
            button_color=theme.PRIMARY,
            button_hover_color=theme.PRIMARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
        )
        self._month_menu.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="w")

    def _build_progress_card(self, parent: ctk.CTkFrame, on_cancel: Callback) -> None:
        card = _card(parent)
        card.grid(row=3, column=0, pady=(0, 4), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(12, 4), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        _section_title(header, "PROGRESO DEL PROCESO").grid(row=0, column=0, sticky="w")
        self._cancel_button = ctk.CTkButton(
            header,
            text="Cancelar",
            width=100,
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color=theme.DANGER,
            text_color=theme.DANGER,
            hover_color=theme.SECONDARY,
            command=on_cancel,
            state="disabled",
        )
        self._cancel_button.grid(row=0, column=1, sticky="e")

        self.progress = ProgressPanel(card)
        self.progress.grid(row=1, column=0, padx=16, pady=(2, 6), sticky="ew")

        self.console = ConsolePanel(card)
        self.console.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="ew")

    # --- Carril derecho ---

    def _build_summary_card(self, rail: ctk.CTkFrame) -> None:
        card = _card(rail)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text="RESUMEN DEL PROCESO  🌿",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.PRIMARY_DARK,
            anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(12, 6), sticky="w")

        self._summary_rows: dict[str, ctk.CTkLabel] = {}
        for index, (key, label) in enumerate(
            (
                ("template", "📄  Plantilla Word"),
                ("excels", "📊  Archivos de profesionales"),
                ("month", "🗓  Mes a procesar"),
                ("activities", "✅  Actividades encontradas"),
                ("items", "≣  Viñetas a insertar"),
            ),
            start=1,
        ):
            line = ctk.CTkFrame(card, fg_color="transparent")
            line.grid(row=index, column=0, padx=14, pady=2, sticky="ew")
            line.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(line, text=label, anchor="w", font=ctk.CTkFont(size=12)).grid(
                row=0, column=0, sticky="w"
            )
            value = ctk.CTkLabel(
                line, text="—", anchor="e", font=ctk.CTkFont(size=12, weight="bold")
            )
            value.grid(row=0, column=1, sticky="e")
            self._summary_rows[key] = value
        ctk.CTkLabel(card, text="", height=4).grid(row=6, column=0)

    def _build_state_card(self, rail: ctk.CTkFrame) -> None:
        card = _card(rail)
        card.grid(row=1, column=0, pady=(10, 0), sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text="ESTADO ACTUAL",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.PRIMARY_DARK,
            anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")
        self._state_label = ctk.CTkLabel(
            card,
            text="Carga la plantilla y los reportes (Excel o Word) para comenzar.",
            anchor="w",
            justify="left",
            wraplength=210,
            text_color=theme.MUTED,
        )
        self._state_label.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")

    def _build_cta(self, rail: ctk.CTkFrame, on_process: Callback) -> None:
        self._process_button = ctk.CTkButton(
            rail,
            text="🌿  PROCESAR Y REVISAR",
            height=52,
            corner_radius=12,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            command=on_process,
        )
        self._process_button.grid(row=3, column=0, sticky="sew", pady=(10, 0))

    # --- API para la ventana ---

    def set_template(self, text: str) -> None:
        self._template_label.configure(
            text=text or "Sin selección",
            text_color=theme.TEXT if text else theme.MUTED,
        )

    def set_output(self, text: str) -> None:
        self._output_label.configure(
            text=text or "Sin selección",
            text_color=theme.TEXT if text else theme.MUTED,
        )

    def set_summary(self, key: str, value: str) -> None:
        label = self._summary_rows.get(key)
        if label is not None:
            label.configure(text=value)

    def set_state_message(self, text: str, *, color: str | tuple[str, str] | None = None) -> None:
        self._state_label.configure(text=text, text_color=color or theme.MUTED)

    def set_running(self, running: bool) -> None:
        self._process_button.configure(state="disabled" if running else "normal")
        self._cancel_button.configure(state="normal" if running else "disabled")
        self._template_button.configure(state="disabled" if running else "normal")
        self._output_button.configure(state="disabled" if running else "normal")
        self._month_menu.configure(state="disabled" if running else "normal")
        self.excel_selector.set_enabled(not running)

    def append_event(self, level: EventLevel, text: str) -> None:
        self.console.append(level, text)
