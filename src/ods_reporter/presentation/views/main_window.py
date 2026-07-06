"""Ventana principal de la aplicación.

Ensambla los componentes y conecta los eventos de la interfaz con el ViewModel.
Consume los mensajes del hilo de trabajo desde el hilo principal mediante un
sondeo periódico de la cola (``after``), de forma segura para tkinter.

Flujo: Revisar y generar → análisis en segundo plano → ventana de vista previa
(con reasignación del contenido sin ubicación) → generación → resumen.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ods_reporter.application.ports.progress_port import EventLevel
from ods_reporter.application.use_cases.ods_plan import ODSPlan, PlanOverrides
from ods_reporter.domain.entities.processing_result import ProcessingResult
from ods_reporter.presentation import theme
from ods_reporter.presentation.system_open import open_path
from ods_reporter.presentation.view_models.main_view_model import FormInputs, MainViewModel
from ods_reporter.presentation.views.components.console_panel import ConsolePanel
from ods_reporter.presentation.views.components.excel_list_selector import ExcelListSelector
from ods_reporter.presentation.views.components.file_selector import FileSelector
from ods_reporter.presentation.views.components.progress_panel import ProgressPanel
from ods_reporter.presentation.views.preview_dialog import PreviewDialog
from ods_reporter.presentation.workers.gui_progress import EventMessage, ProgressMessage
from ods_reporter.shared.constants import APP_NAME, APP_VERSION
from ods_reporter.shared.result import Result

_POLL_INTERVAL_MS = 120


class MainWindow(ctk.CTk):
    """Ventana principal (vista) de ODS Reporter."""

    def __init__(self, view_model: MainViewModel) -> None:
        super().__init__()
        self._vm = view_model
        self._inputs = FormInputs()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("900x740")
        self.minsize(820, 660)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_form()
        self._build_console()
        self._build_footer()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- Construcción de la interfaz ---

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=24, pady=(18, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            titles, text=APP_NAME, font=ctk.CTkFont(size=21, weight="bold")
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles,
            text="Del Excel de cada profesional al informe Word oficial.",
            text_color=theme.MUTED,
        ).pack(anchor="w")

        # Selector de tema (claro/oscuro/sistema), discreto.
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

    @staticmethod
    def _on_change_theme(choice: str) -> None:
        ctk.set_appearance_mode({"Claro": "light", "Oscuro": "dark"}.get(choice, "system"))

    def _build_form(self) -> None:
        form = ctk.CTkFrame(self, fg_color=theme.CARD, corner_radius=12)
        form.grid(row=1, column=0, padx=24, pady=4, sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        self._word_selector = FileSelector(
            form, "Plantilla Word (.docx):", self._browse_word
        )
        self._word_selector.grid(row=0, column=0, padx=14, pady=(14, 2), sticky="ew")

        self._excel_selector = ExcelListSelector(form)
        self._excel_selector.grid(row=1, column=0, padx=14, pady=4, sticky="ew")

        self._output_selector = FileSelector(
            form, "Carpeta de salida:", self._browse_output
        )
        self._output_selector.grid(row=2, column=0, padx=14, pady=2, sticky="ew")

        month_row = ctk.CTkFrame(form, fg_color="transparent")
        month_row.grid(row=3, column=0, padx=14, pady=(2, 14), sticky="ew")
        ctk.CTkLabel(month_row, text="Mes a procesar:", width=150, anchor="w").pack(
            side="left", padx=(0, 8)
        )
        self._month_var = ctk.StringVar(value="")
        self._month_menu = ctk.CTkOptionMenu(
            month_row,
            values=list(self._vm.months),
            variable=self._month_var,
            width=190,
            fg_color=theme.SECONDARY,
            button_color=theme.PRIMARY,
            button_hover_color=theme.PRIMARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
        )
        self._month_menu.pack(side="left")

    def _build_console(self) -> None:
        self._progress = ProgressPanel(self)
        self._progress.grid(row=3, column=0, padx=24, pady=(8, 4), sticky="ew")

        self._console = ConsolePanel(self)
        self._console.grid(row=2, column=0, padx=24, pady=8, sticky="nsew")

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, padx=24, pady=(4, 18), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        self._start_button = ctk.CTkButton(
            footer,
            text="Revisar y generar…",
            width=180,
            height=38,
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            command=self._on_start,
        )
        self._start_button.grid(row=0, column=1, padx=(0, 8))

        self._cancel_button = ctk.CTkButton(
            footer,
            text="Cancelar",
            width=130,
            height=38,
            fg_color="transparent",
            border_width=1,
            border_color=theme.DANGER,
            text_color=theme.DANGER,
            hover_color=("gray92", "gray20"),
            command=self._on_cancel,
            state="disabled",
        )
        self._cancel_button.grid(row=0, column=2)

    # --- Diálogos de selección ---

    def _browse_word(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecciona la plantilla Word",
            filetypes=[("Documentos Word", "*.docx")],
        )
        if path:
            self._inputs.word_template = path
            self._word_selector.set_value(_short(path))

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Selecciona la carpeta de salida")
        if path:
            self._inputs.output_dir = path
            self._output_selector.set_value(_short(path))

    # --- Acciones ---

    def _on_start(self) -> None:
        self._inputs.month = self._month_var.get()
        self._inputs.excel_files = self._excel_selector.get_files()
        self._console.clear()
        self._progress.reset()

        errors = self._vm.start(self._inputs, on_plan_ready=self._on_plan_ready)
        if errors:
            messagebox.showwarning("Faltan datos", "\n".join(errors))
            return

        self._set_running(True)
        self._poll()

    def _on_cancel(self) -> None:
        self._vm.cancel()
        self._console.append(EventLevel.WARNING, "Cancelación solicitada…")
        self._cancel_button.configure(state="disabled")

    # --- Fase 1: análisis y vista previa ---

    def _on_plan_ready(self, result: Result[ODSPlan]) -> None:
        # Se ejecuta desde el hilo de trabajo: se delega al hilo principal.
        self.after(0, lambda: self._handle_plan(result))

    def _handle_plan(self, result: Result[ODSPlan]) -> None:
        self._drain_queue()
        self._set_running(False)
        if result.is_err():
            self._console.append(EventLevel.ERROR, result.error or "Error desconocido")
            messagebox.showerror("Error", result.error or "Ocurrió un error.")
            return

        plan = result.unwrap()
        if plan.cancelled:
            self._progress.set_status("Análisis cancelado.")
            return

        self._progress.set_status("Análisis completo. Revisa la vista previa.")
        PreviewDialog(self, plan, on_confirm=self._start_generation)

    # --- Fase 2: generación ---

    def _start_generation(self, plan: ODSPlan, overrides: PlanOverrides) -> None:
        if not self._vm.generate(plan, overrides, on_done=self._on_done):
            return
        self._set_running(True)
        self._poll()

    def _on_done(self, result: Result[ProcessingResult]) -> None:
        # Se ejecuta desde el hilo de trabajo: se delega al hilo principal.
        self.after(0, lambda: self._handle_result(result))

    def _handle_result(self, result: Result[ProcessingResult]) -> None:
        self._drain_queue()
        self._set_running(False)
        if result.is_err():
            self._console.append(EventLevel.ERROR, result.error or "Error desconocido")
            messagebox.showerror("Error", result.error or "Ocurrió un error.")
            return
        processing = result.unwrap()
        self._progress.complete()
        self._show_summary(processing)

    # --- Sondeo de la cola (hilo principal) ---

    def _poll(self) -> None:
        self._drain_queue()
        if self._vm.is_running:
            self.after(_POLL_INTERVAL_MS, self._poll)

    def _drain_queue(self) -> None:
        queue = self._vm.progress.queue
        while not queue.empty():
            message = queue.get_nowait()
            if isinstance(message, EventMessage):
                self._console.append(message.level, message.text)
            elif isinstance(message, ProgressMessage):
                self._progress.set_progress(message.current, message.total)

    # --- Estado / resumen ---

    def _set_running(self, running: bool) -> None:
        self._start_button.configure(state="disabled" if running else "normal")
        self._cancel_button.configure(state="normal" if running else "disabled")
        for selector in (self._word_selector, self._excel_selector, self._output_selector):
            selector.set_enabled(not running)
        self._month_menu.configure(state="disabled" if running else "normal")

    def _show_summary(self, processing: ProcessingResult) -> None:
        if processing.cancelled:
            self._progress.set_status("Proceso cancelado.")
        else:
            self._progress.set_status(
                f"Completado: {processing.activities_with_content} actividad(es), "
                f"{processing.items_written} viñeta(s). Salida: {processing.output_path}"
            )
        SummaryDialog(self, processing.summary, processing.output_path)

    def _on_close(self) -> None:
        if self._vm.is_running:
            if not messagebox.askyesno("Salir", "Hay un proceso en curso. ¿Cancelar y salir?"):
                return
            self._vm.cancel()
        self.destroy()


class SummaryDialog(ctk.CTkToplevel):
    """Ventana modal con el resumen final del procesamiento."""

    def __init__(self, master: ctk.CTk, summary: str, output_path: str = "") -> None:
        super().__init__(master)
        self._output_path = output_path
        self.title("Resumen del procesamiento")
        self.geometry("640x540")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        textbox = ctk.CTkTextbox(
            self, wrap="word", font=("monospace", 12), fg_color=theme.CONSOLE_BG
        )
        textbox.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        textbox.insert("1.0", summary or "Sin resumen.")
        textbox.configure(state="disabled")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=1, column=0, pady=(0, 16))
        if output_path:
            ctk.CTkButton(
                buttons,
                text="Abrir carpeta de salida",
                fg_color=theme.PRIMARY,
                hover_color=theme.PRIMARY_HOVER,
                command=self._open_output,
            ).pack(side="left", padx=6)
        ctk.CTkButton(
            buttons,
            text="Cerrar",
            fg_color=theme.SECONDARY,
            hover_color=theme.SECONDARY_HOVER,
            text_color=theme.TEXT_ON_SECONDARY,
            command=self.destroy,
        ).pack(side="left", padx=6)
        self.after(100, self.lift)

    def _open_output(self) -> None:
        folder = Path(self._output_path).parent if self._output_path else None
        if folder:
            open_path(folder)


def _short(path: str, max_len: int = 60) -> str:
    """Acorta una ruta larga para mostrarla."""
    return path if len(path) <= max_len else "…" + path[-(max_len - 1) :]
