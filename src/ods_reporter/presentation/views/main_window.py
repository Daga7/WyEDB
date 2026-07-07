"""Ventana principal de la aplicación (shell con navegación lateral).

Estructura: barra lateral (logo + módulos) y un área principal con cabecera,
indicador de pasos y tres vistas intercambiables:

- **Nuevo informe**: carga de archivos, configuración y procesamiento.
- **Resumen detallado**: revisión del análisis (con reasignación del contenido
  sin ubicación), panel de resumen/auditoría y generación del informe.
- **Cómo usar**: el manual de usuario dentro de la aplicación.

La ventana orquesta el ViewModel y consume los mensajes del hilo de trabajo
desde el hilo principal mediante un sondeo periódico de la cola (``after``).
"""

from __future__ import annotations

import queue
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ods_reporter.application.ports.progress_port import EventLevel
from ods_reporter.application.services.professional_auditor import ProfessionalAuditor
from ods_reporter.application.use_cases.ods_plan import ODSPlan
from ods_reporter.domain.entities.processing_result import (
    ProcessingResult,
    ProfessionalAudit,
)
from ods_reporter.presentation import branding, theme
from ods_reporter.presentation.system_open import open_path
from ods_reporter.presentation.view_models.main_view_model import FormInputs, MainViewModel
from ods_reporter.presentation.views.components.sidebar import (
    HELP,
    NEW_REPORT,
    REVIEW,
    Sidebar,
)
from ods_reporter.presentation.views.components.stepper import Stepper, StepState
from ods_reporter.presentation.views.help_view import HelpView
from ods_reporter.presentation.views.new_report_view import NewReportView
from ods_reporter.presentation.views.review_view import ReviewView
from ods_reporter.presentation.workers.gui_progress import EventMessage, ProgressMessage
from ods_reporter.shared.constants import APP_NAME, APP_VERSION
from ods_reporter.shared.result import Result

_POLL_INTERVAL_MS = 120

_STEPS = ["Plantilla", "Excel", "Configuración", "Validación", "Generar"]


class MainWindow(ctk.CTk):
    """Ventana principal (vista) de ODS Reporter."""

    def __init__(self, view_model: MainViewModel) -> None:
        super().__init__(fg_color=theme.BG)
        self._vm = view_model
        self._inputs = FormInputs()
        self._plan: ODSPlan | None = None
        self._audit: ProfessionalAudit | None = None
        self._result: ProcessingResult | None = None
        self._phase = "idle"  # idle | planning | review | applying | done
        # Resultados llegados desde el hilo de trabajo. En Python 3.13+ tkinter
        # no permite llamar ``after`` desde otro hilo: el worker solo ENCOLA y
        # el sondeo del hilo principal despacha.
        self._pending: queue.Queue[tuple[str, object]] = queue.Queue()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1280x820")
        self.minsize(1140, 700)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        branding.apply_window_icon(self)

        self._sidebar = Sidebar(self, on_select=self._on_select_module)
        self._sidebar.grid(row=0, column=0, sticky="nsw")

        self._build_main_area()
        self._refresh()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- Construcción ---

    def _build_main_area(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=22, pady=(16, 18))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        # Cabecera
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            titles,
            text="Automatización de informes ambientales",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles,
            text="Del Excel de cada profesional al informe Word oficial.",
            text_color=theme.MUTED,
        ).pack(anchor="w")
        self._theme_menu = ctk.CTkOptionMenu(
            header,
            values=["Sistema", "Claro", "Oscuro"],
            width=104,
            height=28,
            fg_color=theme.SECONDARY,
            button_color=theme.SECONDARY,
            button_hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=self._on_change_theme,
        )
        self._theme_menu.grid(row=0, column=1, sticky="ne")

        # Pasos del flujo
        self._stepper = Stepper(main, _STEPS)
        self._stepper.grid(row=1, column=0, pady=(14, 12), sticky="ew")

        # Contenedor de vistas
        container = ctk.CTkFrame(main, fg_color="transparent")
        container.grid(row=2, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self._new_report = NewReportView(
            container,
            months=self._vm.months,
            on_browse_word=self._browse_word,
            on_browse_output=self._browse_output,
            on_process=self._on_process,
            on_cancel=self._on_cancel,
            on_inputs_changed=self._refresh,
        )
        self._new_report.grid(row=0, column=0, sticky="nsew")

        self._review = ReviewView(
            container,
            on_back=lambda: self._sidebar.select(NEW_REPORT),
            on_generate=self._on_generate,
            on_open_folder=self._open_output_folder,
            on_new_report=lambda: self._sidebar.select(NEW_REPORT),
        )
        self._review.grid(row=0, column=0, sticky="nsew")
        self._review.grid_remove()

        self._help = HelpView(container)
        self._help.grid(row=0, column=0, sticky="nsew")
        self._help.grid_remove()

    # --- Navegación ---

    def _on_select_module(self, key: str) -> None:
        views = {NEW_REPORT: self._new_report, REVIEW: self._review, HELP: self._help}
        for name, view in views.items():
            if name == key:
                view.grid()
            else:
                view.grid_remove()

    # --- Diálogos de selección ---

    def _browse_word(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecciona la plantilla Word",
            filetypes=[("Documentos Word", "*.docx")],
        )
        if path:
            self._inputs.word_template = path
            self._new_report.set_template(Path(path).name)
            self._refresh()

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Selecciona la carpeta de salida")
        if path:
            self._inputs.output_dir = path
            self._new_report.set_output(_short(path))
            self._refresh()

    # --- Fase 1: análisis ---

    def _on_process(self) -> None:
        self._inputs.month = self._new_report.month_var.get()
        self._inputs.excel_files = self._new_report.excel_selector.get_files()
        self._new_report.console.clear()
        self._new_report.progress.reset()

        errors = self._vm.start(self._inputs, on_plan_ready=self._on_plan_ready)
        if errors:
            messagebox.showwarning("Faltan datos", "\n".join(errors))
            return

        self._plan = None
        self._result = None
        self._phase = "planning"
        self._set_running(True)
        self._refresh()
        self._poll()

    def _on_plan_ready(self, result: Result[ODSPlan]) -> None:
        # Se ejecuta desde el hilo de trabajo: solo encola (sin tocar tkinter).
        self._pending.put(("plan", result))

    def _handle_plan(self, result: Result[ODSPlan]) -> None:
        self._drain_queue()
        self._set_running(False)
        if result.is_err():
            self._phase = "idle"
            self._refresh()
            messagebox.showerror("Error", result.error or "Ocurrió un error.")
            return

        plan = result.unwrap()
        if plan.cancelled:
            self._phase = "idle"
            self._refresh()
            self._new_report.progress.set_status("Análisis cancelado.")
            return

        self._plan = plan
        self._audit = ProfessionalAuditor().audit(list(plan.professionals))
        self._phase = "review"
        self._review.populate(plan, self._audit)
        self._refresh()
        self._new_report.progress.set_status("Análisis completo. Revisa el resumen detallado.")
        self._sidebar.select(REVIEW)

    # --- Fase 2: generación ---

    def _on_generate(self) -> None:
        if self._plan is None:
            return
        overrides = self._review.get_overrides()
        if not self._vm.generate(self._plan, overrides, on_done=self._on_done):
            return
        self._phase = "applying"
        self._set_running(True)
        self._review.set_generating(True)
        self._refresh()
        self._poll()

    def _on_done(self, result: Result[ProcessingResult]) -> None:
        # Se ejecuta desde el hilo de trabajo: solo encola (sin tocar tkinter).
        self._pending.put(("result", result))

    def _handle_result(self, result: Result[ProcessingResult]) -> None:
        self._drain_queue()
        self._set_running(False)
        self._review.set_generating(False)
        if result.is_err():
            self._phase = "review"
            self._refresh()
            messagebox.showerror("Error", result.error or "Ocurrió un error.")
            return

        processing = result.unwrap()
        self._result = processing
        self._phase = "done"
        self._new_report.progress.complete()
        self._new_report.progress.set_status(
            f"Completado: {processing.activities_with_content} actividad(es), "
            f"{processing.items_written} viñeta(s)."
        )
        audit = processing.audit or self._audit or ProfessionalAudit()
        self._review.show_result(processing, audit)
        self._refresh()

    # --- Acciones auxiliares ---

    def _on_cancel(self) -> None:
        self._vm.cancel()
        self._new_report.console.append(EventLevel.WARNING, "Cancelación solicitada…")

    def _open_output_folder(self) -> None:
        if self._result and self._result.output_path:
            open_path(Path(self._result.output_path).parent)

    @staticmethod
    def _on_change_theme(choice: str) -> None:
        ctk.set_appearance_mode({"Claro": "light", "Oscuro": "dark"}.get(choice, "system"))

    # --- Sondeo de la cola (hilo principal) ---

    def _poll(self) -> None:
        self._drain_queue()
        self._dispatch_pending()
        if self._vm.is_running or not self._pending.empty():
            self.after(_POLL_INTERVAL_MS, self._poll)

    def _dispatch_pending(self) -> None:
        """Despacha en el hilo principal los resultados llegados del worker."""
        while not self._pending.empty():
            kind, payload = self._pending.get_nowait()
            if kind == "plan":
                self._handle_plan(payload)  # type: ignore[arg-type]
            elif kind == "result":
                self._handle_result(payload)  # type: ignore[arg-type]

    def _drain_queue(self) -> None:
        events = self._vm.progress.queue
        while not events.empty():
            message = events.get_nowait()
            if isinstance(message, EventMessage):
                self._new_report.console.append(message.level, message.text)
            elif isinstance(message, ProgressMessage):
                self._new_report.progress.set_progress(message.current, message.total)

    # --- Estado visual ---

    def _set_running(self, running: bool) -> None:
        self._new_report.set_running(running)

    def _refresh(self) -> None:
        """Recalcula stepper, resumen del carril derecho y mensaje de estado."""
        template_ok = bool(self._inputs.word_template)
        excel_count = len(self._new_report.excel_selector.get_files())
        month = self._new_report.month_var.get()
        config_ok = bool(self._inputs.output_dir) and bool(month)

        states: list[StepState] = [
            "done" if template_ok else "pending",
            "done" if excel_count else "pending",
            "done" if config_ok else "pending",
            "active" if self._phase == "planning" else (
                "done" if self._plan is not None else "pending"
            ),
            "active" if self._phase == "applying" else (
                "done" if self._result is not None else "pending"
            ),
        ]
        self._stepper.set_states(states)

        view = self._new_report
        view.set_summary("template", "1 archivo" if template_ok else "—")
        view.set_summary("excels", f"{excel_count} archivo(s)" if excel_count else "—")
        view.set_summary("month", month.capitalize() if month else "—")
        if self._plan is not None:
            total_items = sum(p.items_count for p in self._plan.planned if p.matched)
            view.set_summary("activities", str(len(self._plan.planned)))
            view.set_summary("items", str(total_items))
        else:
            view.set_summary("activities", "—")
            view.set_summary("items", "—")

        if self._phase == "planning":
            view.set_state_message("Analizando archivos…", color=theme.PRIMARY)
        elif self._phase == "applying":
            view.set_state_message("Generando el informe…", color=theme.PRIMARY)
        elif self._phase == "done":
            view.set_state_message("✓ Informe generado. Revisa el resumen detallado.",
                                   color=theme.PRIMARY)
        elif self._phase == "review":
            view.set_state_message(
                "Análisis listo. Revisa y confirma en «Resumen detallado».",
                color=theme.PRIMARY,
            )
        elif template_ok and excel_count and config_ok:
            view.set_state_message("✓ Listo para procesar.", color=theme.PRIMARY)
        else:
            missing = []
            if not template_ok:
                missing.append("plantilla Word")
            if not excel_count:
                missing.append("archivos Excel")
            if not config_ok:
                missing.append("carpeta de salida y mes")
            view.set_state_message("Falta: " + ", ".join(missing) + ".")

    def _on_close(self) -> None:
        if self._vm.is_running:
            if not messagebox.askyesno("Salir", "Hay un proceso en curso. ¿Cancelar y salir?"):
                return
            self._vm.cancel()
        self.destroy()


def _short(path: str, max_len: int = 46) -> str:
    """Acorta una ruta larga para mostrarla."""
    return path if len(path) <= max_len else "…" + path[-(max_len - 1) :]
