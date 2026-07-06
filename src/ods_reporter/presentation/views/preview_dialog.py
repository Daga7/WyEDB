"""Ventana de vista previa del informe antes de generarlo.

Muestra el plan de inserción (qué recibirá cada actividad del Word), los
errores y advertencias del análisis y, para el contenido que no encontró su
actividad en el Word, permite elegir manualmente el numeral de destino o
omitirlo. Solo al confirmar se escribe el documento.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ods_reporter.application.use_cases.ods_plan import ODSPlan, PlanOverrides
from ods_reporter.infrastructure.matching.roman_numerals import int_to_roman
from ods_reporter.presentation import branding, theme

ConfirmCallback = Callable[[ODSPlan, PlanOverrides], None]

_OMIT_OPTION = "No insertar (omitir)"


class PreviewDialog(ctk.CTkToplevel):
    """Vista previa modal: resume el plan y captura las decisiones del usuario."""

    def __init__(
        self, master: ctk.CTk, plan: ODSPlan, on_confirm: ConfirmCallback
    ) -> None:
        super().__init__(master)
        self._plan = plan
        self._on_confirm = on_confirm
        # Elección del usuario por cada actividad sin ubicación (clave del plan).
        self._choices: dict[tuple[int, int], ctk.StringVar] = {}
        self._option_to_ordinal: dict[str, int] = {}

        self.title(f"Vista previa — {plan.month.capitalize()}")
        self.geometry("800x680")
        self.minsize(680, 560)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        branding.apply_window_icon(self)

        self._build_header()
        self._build_body()
        self._build_footer()

        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        # El grab inmediato falla si la ventana aún no está mapeada.
        self.after(150, self._grab)

    # --- Construcción ---

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(18, 6), sticky="ew")

        ctk.CTkLabel(
            header,
            text="Revisa lo que se va a insertar",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(header, text=self._summary_text(), text_color=theme.MUTED).pack(
            anchor="w"
        )

    def _summary_text(self) -> str:
        plan = self._plan
        total_items = sum(p.items_count for p in plan.planned if p.matched)
        parts = [
            f"{len(plan.professionals)} profesional(es)",
            f"{total_items} viñeta(s) para {len(plan.word_activities)} actividad(es) del Word",
        ]
        if plan.other_activities_count:
            parts.append(f"{plan.other_activities_count} adicional(es)")
        if plan.unmatched:
            parts.append(f"{len(plan.unmatched)} sin ubicación")
        if plan.read_errors:
            parts.append(f"{len(plan.read_errors)} archivo(s) con error")
        return " · ".join(parts)

    def _build_body(self) -> None:
        body = ctk.CTkScrollableFrame(self, fg_color=theme.CARD, corner_radius=12)
        body.grid(row=1, column=0, padx=24, pady=6, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        row = 0

        row = self._build_word_section(body, row)
        if self._plan.unmatched:
            row = self._build_unmatched_section(body, row)
        if self._plan.read_errors or self._plan.warnings:
            row = self._build_issues_section(body, row)

    def _build_word_section(self, parent: ctk.CTkFrame, row: int) -> int:
        row = self._section_label(parent, "Actividades del Word", row)
        for overview in self._plan.word_activities:
            items = self._plan.items_for_word_ordinal(overview.ordinal)
            line = ctk.CTkFrame(parent, fg_color="transparent")
            line.grid(row=row, column=0, padx=14, pady=1, sticky="ew")
            line.grid_columnconfigure(0, weight=1)

            label = f"{int_to_roman(overview.ordinal)}.  {_short(overview.label, 72)}"
            ctk.CTkLabel(line, text=label, anchor="w").grid(row=0, column=0, sticky="ew")
            if items:
                status, color = f"{items} viñeta(s)", theme.GREEN
            else:
                status, color = "texto estándar", theme.MUTED
            ctk.CTkLabel(line, text=status, text_color=color, anchor="e").grid(
                row=0, column=1, padx=(8, 0)
            )
            row += 1

        if self._plan.word_has_other_section:
            row = self._build_other_activities_row(parent, row)
        return row

    def _build_other_activities_row(self, parent: ctk.CTkFrame, row: int) -> int:
        line = ctk.CTkFrame(parent, fg_color="transparent")
        line.grid(row=row, column=0, padx=14, pady=(6, 1), sticky="ew")
        line.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            line, text="Observaciones y actividades adicionales", anchor="w"
        ).grid(row=0, column=0, sticky="ew")
        count = self._plan.other_activities_count
        if count:
            status, color = f"{count} viñeta(s)", theme.GREEN
        else:
            status, color = "sin adicionales", theme.MUTED
        ctk.CTkLabel(line, text=status, text_color=color, anchor="e").grid(
            row=0, column=1, padx=(8, 0)
        )
        return row + 1

    def _build_unmatched_section(self, parent: ctk.CTkFrame, row: int) -> int:
        row = self._section_label(parent, "Contenido sin ubicación", row)
        ctk.CTkLabel(
            parent,
            text="Estas actividades del Excel no existen en el Word. "
            "Elige en qué numeral insertar cada una, o déjala sin insertar.",
            text_color=theme.MUTED,
            anchor="w",
            wraplength=640,
            justify="left",
        ).grid(row=row, column=0, padx=14, pady=(0, 6), sticky="ew")
        row += 1

        options = [_OMIT_OPTION]
        for overview in self._plan.word_activities:
            display = f"{int_to_roman(overview.ordinal)}. {_short(overview.label, 38)}"
            self._option_to_ordinal[display] = overview.ordinal
            options.append(display)

        for planned in self._plan.unmatched:
            card = ctk.CTkFrame(parent, fg_color=theme.CARD_INNER, corner_radius=8)
            card.grid(row=row, column=0, padx=14, pady=3, sticky="ew")
            card.grid_columnconfigure(0, weight=1)

            title = f"Actividad {planned.ordinal} · {_short(planned.label, 58)}"
            detail = (
                f"{planned.professional_name} — {planned.source_file}"
                f" · {planned.items_count} viñeta(s)"
            )
            ctk.CTkLabel(card, text=title, anchor="w").grid(
                row=0, column=0, padx=10, pady=(6, 0), sticky="ew"
            )
            ctk.CTkLabel(
                card, text=detail, text_color=theme.MUTED, anchor="w"
            ).grid(row=1, column=0, padx=10, pady=(0, 6), sticky="ew")

            variable = ctk.StringVar(value=_OMIT_OPTION)
            self._choices[planned.key] = variable
            ctk.CTkOptionMenu(
                card,
                values=options,
                variable=variable,
                width=260,
                fg_color=theme.SECONDARY,
                button_color=theme.PRIMARY,
                button_hover_color=theme.PRIMARY_HOVER,
                text_color=theme.TEXT_ON_SECONDARY,
            ).grid(row=0, column=1, rowspan=2, padx=10, pady=6)
            row += 1
        return row

    def _build_issues_section(self, parent: ctk.CTkFrame, row: int) -> int:
        plan = self._plan
        title = (
            f"Errores ({len(plan.read_errors)}) y advertencias ({len(plan.warnings)})"
        )
        row = self._section_label(parent, title, row)
        textbox = ctk.CTkTextbox(
            parent,
            height=110,
            wrap="word",
            font=("monospace", 11),
            fg_color=theme.CONSOLE_BG,
            text_color=theme.CONSOLE_TEXT,
        )
        textbox.grid(row=row, column=0, padx=14, pady=(0, 10), sticky="ew")
        for error in plan.read_errors:
            textbox.insert("end", f"✖ {error}\n")
        for warning in plan.warnings:
            textbox.insert("end", f"⚠ {warning}\n")
        textbox.configure(state="disabled")
        return row + 1

    @staticmethod
    def _section_label(parent: ctk.CTkFrame, text: str, row: int) -> int:
        label = ctk.CTkLabel(
            parent,
            text=text.upper(),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=theme.MUTED,
            anchor="w",
        )
        label.grid(row=row, column=0, padx=14, pady=(12, 4), sticky="ew")
        return row + 1

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, padx=24, pady=(6, 18), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer,
            text="No se escribirá nada hasta que confirmes.",
            text_color=theme.MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer,
            text="Cancelar",
            width=120,
            height=36,
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=self._on_cancel,
        ).grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            footer,
            text="Generar informe",
            width=170,
            height=36,
            fg_color=theme.GREEN,
            hover_color=theme.GREEN_HOVER,
            command=self._on_generate,
        ).grid(row=0, column=2)

    # --- Acciones ---

    def _grab(self) -> None:
        try:
            self.grab_set()
        except Exception:  # noqa: BLE001 - si el grab falla, la ventana sigue usable
            pass

    def _on_cancel(self) -> None:
        self.grab_release()
        self.destroy()

    def _on_generate(self) -> None:
        overrides: PlanOverrides = {}
        for key, variable in self._choices.items():
            choice = variable.get()
            overrides[key] = self._option_to_ordinal.get(choice)
        self.grab_release()
        self.destroy()
        self._on_confirm(self._plan, overrides)


def _short(text: str, max_len: int) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= max_len else cleaned[: max_len - 1] + "…"
