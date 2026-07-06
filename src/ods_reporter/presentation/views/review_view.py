"""Módulo "Resumen detallado": revisión del análisis antes de generar.

Dos secciones:

- **Izquierda**: todo lo que se va a insertar (estado por actividad del Word,
  actividades adicionales y el contenido sin ubicación con su menú para elegir
  numeral destino u omitir), más las acciones (volver / generar). Tras generar,
  muestra el resultado con acceso a la carpeta de salida.
- **Derecha**: panel de resumen del procesamiento (contadores, auditoría de
  profesionales y advertencias/errores).
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from ods_reporter.application.use_cases.ods_plan import ODSPlan, PlanOverrides
from ods_reporter.domain.entities.processing_result import (
    ProcessingResult,
    ProfessionalAudit,
)
from ods_reporter.infrastructure.matching.roman_numerals import int_to_roman
from ods_reporter.presentation import theme
from ods_reporter.shared.constants import MIN_ACTIVITIES_THRESHOLD

Callback = Callable[[], None]

_OMIT_OPTION = "No insertar (omitir)"


def _card(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=theme.CARD,
        corner_radius=12,
        border_width=1,
        border_color=theme.BORDER,
    )


def _short(text: str, max_len: int) -> str:
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= max_len else cleaned[: max_len - 1] + "…"


class ReviewView(ctk.CTkFrame):
    """Vista de revisión y resumen (módulo 2)."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_back: Callback,
        on_generate: Callback,
        on_open_folder: Callback,
        on_new_report: Callback,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_back = on_back
        self._on_generate = on_generate
        self._on_open_folder = on_open_folder
        self._on_new_report = on_new_report

        self._plan: ODSPlan | None = None
        self._choices: dict[tuple[int, int], ctk.StringVar] = {}
        self._option_to_ordinal: dict[str, int] = {}

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # Sección izquierda: revisión + acciones.
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)
        self._left_body = _card(left)
        self._left_body.grid(row=0, column=0, sticky="nsew")
        self._left_body.grid_columnconfigure(0, weight=1)
        self._left_body.grid_rowconfigure(1, weight=1)
        self._build_actions(left)

        # Sección derecha: panel de resumen.
        self._right_body = _card(self)
        self._right_body.grid(row=0, column=1, sticky="nsew")
        self._right_body.grid_columnconfigure(0, weight=1)
        self._right_body.grid_rowconfigure(1, weight=1)

        self._show_empty_state()

    # --- Estados de la sección izquierda ---

    def _clear(self, frame: ctk.CTkFrame) -> None:
        for child in frame.winfo_children():
            child.destroy()

    def _show_empty_state(self) -> None:
        self._clear(self._left_body)
        self._clear(self._right_body)
        ctk.CTkLabel(
            self._left_body,
            text="Aún no hay un procesamiento para revisar.\n\n"
            "Ve a «Nuevo informe», carga los archivos y pulsa\n«Procesar y revisar».",
            text_color=theme.MUTED,
            justify="center",
        ).grid(row=0, column=0, padx=30, pady=60)
        ctk.CTkLabel(
            self._right_body,
            text="El resumen del procesamiento\naparecerá aquí.",
            text_color=theme.MUTED,
            justify="center",
        ).grid(row=0, column=0, padx=30, pady=60)
        self._generate_button.configure(state="disabled")
        self._back_button.configure(state="normal")

    def _build_actions(self, parent: ctk.CTkFrame) -> None:
        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=1, column=0, pady=(10, 0), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)

        self._hint_label = ctk.CTkLabel(
            actions,
            text="No se escribirá nada hasta que confirmes.",
            text_color=theme.MUTED,
            anchor="w",
        )
        self._hint_label.grid(row=0, column=0, sticky="w")

        self._back_button = ctk.CTkButton(
            actions,
            text="←  Volver",
            width=110,
            height=40,
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=self._on_back,
        )
        self._back_button.grid(row=0, column=1, padx=(0, 8))

        self._generate_button = ctk.CTkButton(
            actions,
            text="🌿  GENERAR INFORME",
            width=210,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            command=self._on_generate,
            state="disabled",
        )
        self._generate_button.grid(row=0, column=2)

    # --- Población con el plan ---

    def populate(self, plan: ODSPlan, audit: ProfessionalAudit) -> None:
        """Muestra el plan analizado y el resumen (antes de generar)."""
        self._plan = plan
        self._choices = {}
        self._option_to_ordinal = {}
        self._clear(self._left_body)
        self._clear(self._right_body)

        ctk.CTkLabel(
            self._left_body,
            text="🔎  Revisión del contenido a insertar",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")

        scroll = ctk.CTkScrollableFrame(self._left_body, fg_color="transparent")
        scroll.grid(row=1, column=0, padx=8, pady=(0, 10), sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        row = 0
        row = self._build_word_rows(scroll, row)
        if plan.unmatched:
            row = self._build_unmatched_section(scroll, row)

        self._populate_summary_panel(plan, audit)
        self._generate_button.configure(state="normal", text="🌿  GENERAR INFORME")
        self._back_button.configure(state="normal")
        self._hint_label.configure(text="No se escribirá nada hasta que confirmes.")

    def _build_word_rows(self, parent: ctk.CTkFrame, row: int) -> int:
        assert self._plan is not None
        plan = self._plan
        for overview in plan.word_activities:
            items = plan.items_for_word_ordinal(overview.ordinal)
            line = ctk.CTkFrame(parent, fg_color="transparent")
            line.grid(row=row, column=0, padx=8, pady=1, sticky="ew")
            line.grid_columnconfigure(0, weight=1)
            label = f"{int_to_roman(overview.ordinal)}.  {_short(overview.label, 64)}"
            ctk.CTkLabel(line, text=label, anchor="w").grid(row=0, column=0, sticky="ew")
            if items:
                status, color = f"{items} viñeta(s)", theme.PRIMARY
            else:
                status, color = "texto estándar", theme.MUTED
            ctk.CTkLabel(line, text=status, text_color=color, anchor="e").grid(
                row=0, column=1, padx=(8, 0)
            )
            row += 1

        if plan.word_has_other_section:
            line = ctk.CTkFrame(parent, fg_color="transparent")
            line.grid(row=row, column=0, padx=8, pady=(6, 1), sticky="ew")
            line.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                line, text="Observaciones y actividades adicionales", anchor="w"
            ).grid(row=0, column=0, sticky="ew")
            count = plan.other_activities_count
            status = f"{count} viñeta(s)" if count else "sin adicionales"
            color = theme.PRIMARY if count else theme.MUTED
            ctk.CTkLabel(line, text=status, text_color=color, anchor="e").grid(
                row=0, column=1, padx=(8, 0)
            )
            row += 1
        return row

    def _build_unmatched_section(self, parent: ctk.CTkFrame, row: int) -> int:
        assert self._plan is not None
        plan = self._plan
        ctk.CTkLabel(
            parent,
            text="CONTENIDO SIN UBICACIÓN",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=theme.WARNING,
            anchor="w",
        ).grid(row=row, column=0, padx=8, pady=(14, 2), sticky="w")
        row += 1
        ctk.CTkLabel(
            parent,
            text="Estas actividades del Excel no existen en el Word. Elige en qué "
            "numeral insertar cada una, o déjala sin insertar.",
            text_color=theme.MUTED,
            anchor="w",
            wraplength=520,
            justify="left",
        ).grid(row=row, column=0, padx=8, pady=(0, 6), sticky="ew")
        row += 1

        options = [_OMIT_OPTION]
        for overview in plan.word_activities:
            display = f"{int_to_roman(overview.ordinal)}. {_short(overview.label, 36)}"
            self._option_to_ordinal[display] = overview.ordinal
            options.append(display)

        for planned in plan.unmatched:
            card = ctk.CTkFrame(parent, fg_color=theme.CARD_INNER, corner_radius=8)
            card.grid(row=row, column=0, padx=8, pady=3, sticky="ew")
            card.grid_columnconfigure(0, weight=1)
            title = f"Actividad {planned.ordinal} · {_short(planned.label, 52)}"
            detail = (
                f"{planned.professional_name} — {planned.source_file}"
                f" · {planned.items_count} viñeta(s)"
            )
            ctk.CTkLabel(card, text=title, anchor="w").grid(
                row=0, column=0, padx=10, pady=(6, 0), sticky="ew"
            )
            ctk.CTkLabel(card, text=detail, text_color=theme.MUTED, anchor="w").grid(
                row=1, column=0, padx=10, pady=(0, 6), sticky="ew"
            )
            variable = ctk.StringVar(value=_OMIT_OPTION)
            self._choices[planned.key] = variable
            ctk.CTkOptionMenu(
                card,
                values=options,
                variable=variable,
                width=240,
                fg_color=theme.CARD,
                button_color=theme.PRIMARY,
                button_hover_color=theme.PRIMARY_HOVER,
                text_color=theme.TEXT_ON_SECONDARY,
            ).grid(row=0, column=1, rowspan=2, padx=10, pady=6)
            row += 1
        return row

    # --- Panel derecho: resumen ---

    def _populate_summary_panel(
        self,
        plan: ODSPlan,
        audit: ProfessionalAudit,
        result: ProcessingResult | None = None,
    ) -> None:
        self._clear(self._right_body)
        ctk.CTkLabel(
            self._right_body,
            text="RESUMEN DEL PROCESAMIENTO  🌿",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.PRIMARY_DARK,
            anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(12, 6), sticky="w")

        scroll = ctk.CTkScrollableFrame(self._right_body, fg_color="transparent")
        scroll.grid(row=1, column=0, padx=6, pady=(0, 10), sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        row = 0

        total_items = sum(p.items_count for p in plan.planned if p.matched)
        counters: list[tuple[str, str]] = [
            ("👥  Profesionales", str(len(plan.professionals))),
            ("✅  Actividades con contenido", str(sum(1 for p in plan.planned if p.matched))),
            ("≣  Viñetas", str(result.items_written if result else total_items)),
            ("➕  Actividades adicionales", str(plan.other_activities_count)),
            ("❓  Sin ubicación", str(len(plan.unmatched))),
        ]
        if result is not None:
            counters.append(("📄  Slots con texto estándar", str(result.default_slots_filled)))
        for label, value in counters:
            line = ctk.CTkFrame(scroll, fg_color="transparent")
            line.grid(row=row, column=0, padx=8, pady=2, sticky="ew")
            line.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(line, text=label, anchor="w", font=ctk.CTkFont(size=12)).grid(
                row=0, column=0, sticky="w"
            )
            ctk.CTkLabel(
                line, text=value, anchor="e", font=ctk.CTkFont(size=12, weight="bold")
            ).grid(row=0, column=1, sticky="e")
            row += 1

        row = self._build_audit_section(scroll, row, audit)
        row = self._build_issues_section(scroll, row, plan, result)

    def _build_audit_section(
        self, parent: ctk.CTkFrame, row: int, audit: ProfessionalAudit
    ) -> int:
        ctk.CTkLabel(
            parent,
            text="AUDITORÍA DE PROFESIONALES",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=theme.PRIMARY_DARK,
            anchor="w",
        ).grid(row=row, column=0, padx=8, pady=(14, 4), sticky="w")
        row += 1

        if not audit.without_activities and not audit.below_threshold:
            ctk.CTkLabel(
                parent,
                text="✓ Todos los profesionales cumplen el mínimo.",
                text_color=theme.PRIMARY,
                anchor="w",
            ).grid(row=row, column=0, padx=8, pady=1, sticky="w")
            return row + 1

        for name in audit.without_activities:
            ctk.CTkLabel(
                parent,
                text=f"⚠  {name}: sin actividades reportadas",
                text_color=theme.WARNING,
                anchor="w",
                wraplength=330,
                justify="left",
            ).grid(row=row, column=0, padx=8, pady=1, sticky="w")
            row += 1
        for name, count in audit.below_threshold:
            ctk.CTkLabel(
                parent,
                text=f"⚠  {name}: solo {count} actividad(es) "
                f"(mínimo {MIN_ACTIVITIES_THRESHOLD})",
                text_color=theme.WARNING,
                anchor="w",
                wraplength=330,
                justify="left",
            ).grid(row=row, column=0, padx=8, pady=1, sticky="w")
            row += 1
        return row

    def _build_issues_section(
        self,
        parent: ctk.CTkFrame,
        row: int,
        plan: ODSPlan,
        result: ProcessingResult | None,
    ) -> int:
        errors = list(result.errors) if result is not None else list(plan.read_errors)
        warnings = list(result.warnings) if result is not None else list(plan.warnings)
        if not errors and not warnings:
            return row

        ctk.CTkLabel(
            parent,
            text=f"ERRORES ({len(errors)}) Y ADVERTENCIAS ({len(warnings)})",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=theme.DANGER if errors else theme.WARNING,
            anchor="w",
        ).grid(row=row, column=0, padx=8, pady=(14, 4), sticky="w")
        row += 1

        textbox = ctk.CTkTextbox(
            parent,
            height=150,
            wrap="word",
            font=("monospace", 11),
            fg_color=theme.CONSOLE_BG,
            text_color=theme.CONSOLE_TEXT,
        )
        textbox.grid(row=row, column=0, padx=8, pady=(0, 8), sticky="ew")
        for error in errors:
            textbox.insert("end", f"✖ {error}\n")
        for warning in warnings:
            textbox.insert("end", f"⚠ {warning}\n")
        textbox.configure(state="disabled")
        return row + 1

    # --- Generación y resultado ---

    def get_overrides(self) -> PlanOverrides:
        overrides: PlanOverrides = {}
        for key, variable in self._choices.items():
            overrides[key] = self._option_to_ordinal.get(variable.get())
        return overrides

    def set_generating(self, generating: bool) -> None:
        state = "disabled" if generating else "normal"
        self._generate_button.configure(state=state)
        self._back_button.configure(state=state)
        if generating:
            self._hint_label.configure(text="Generando informe…", text_color=theme.PRIMARY)

    def show_result(self, result: ProcessingResult, audit: ProfessionalAudit) -> None:
        """Muestra el desenlace de la generación en la sección izquierda."""
        self._clear(self._left_body)

        card = ctk.CTkFrame(self._left_body, fg_color="transparent")
        card.grid(row=0, column=0, padx=24, pady=24, sticky="new")
        card.grid_columnconfigure(0, weight=1)

        if result.cancelled:
            icon, title, color = "⚠", "Proceso cancelado", theme.WARNING
            detail = "El informe quedó incompleto. Puedes volver a procesar."
        elif result.has_errors:
            icon, title, color = "⚠", "Informe generado con errores", theme.WARNING
            detail = "Revisa el panel de la derecha y los archivos indicados."
        else:
            icon, title, color = "✅", "Informe generado correctamente", theme.PRIMARY
            detail = "El documento quedó en la carpeta de salida."

        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=40)).grid(row=0, column=0)
        ctk.CTkLabel(
            card, text=title, font=ctk.CTkFont(size=17, weight="bold"), text_color=color
        ).grid(row=1, column=0, pady=(6, 2))
        ctk.CTkLabel(card, text=detail, text_color=theme.MUTED).grid(row=2, column=0)
        if result.output_path:
            ctk.CTkLabel(
                card, text=_short(result.output_path, 70), text_color=theme.MUTED
            ).grid(row=3, column=0, pady=(2, 10))

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=4, column=0, pady=(8, 0))
        if result.output_path:
            ctk.CTkButton(
                buttons,
                text="📁  Abrir carpeta de salida",
                height=38,
                fg_color=theme.PRIMARY,
                hover_color=theme.PRIMARY_HOVER,
                command=self._on_open_folder,
            ).pack(side="left", padx=6)
        ctk.CTkButton(
            buttons,
            text="Nuevo informe",
            height=38,
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=self._on_new_report,
        ).pack(side="left", padx=6)

        if self._plan is not None:
            self._populate_summary_panel(self._plan, audit, result)
        self._generate_button.configure(state="disabled", text="✓  INFORME GENERADO")
        self._back_button.configure(state="normal")
        self._hint_label.configure(
            text="Resumen actualizado con el resultado final.", text_color=theme.MUTED
        )
