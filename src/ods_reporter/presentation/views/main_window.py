"""Ventana principal de la aplicación.

Ensambla los componentes y conecta los eventos de la interfaz con el ViewModel.
Consume los mensajes del hilo de trabajo desde el hilo principal mediante un
sondeo periódico de la cola (``after``), de forma segura para tkinter.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ods_reporter.application.ports.progress_port import EventLevel
from ods_reporter.domain.entities.processing_result import ProcessingResult
from ods_reporter.presentation.system_open import open_path
from ods_reporter.presentation.view_models.main_view_model import FormInputs, MainViewModel
from ods_reporter.presentation.views.components.console_panel import ConsolePanel
from ods_reporter.presentation.views.components.excel_list_selector import ExcelListSelector
from ods_reporter.presentation.views.components.file_selector import FileSelector
from ods_reporter.presentation.views.components.progress_panel import ProgressPanel
from ods_reporter.presentation.workers.gui_progress import EventMessage, ProgressMessage
from ods_reporter.shared.constants import APP_NAME, APP_VERSION, EXCEL_EXTENSIONS, WORD_EXTENSIONS
from ods_reporter.shared.result import Result

_POLL_INTERVAL_MS = 120


class MainWindow(ctk.CTk):
    """Ventana principal (vista) de ODS Reporter."""

    def __init__(self, view_model: MainViewModel) -> None:
        super().__init__()
        self._vm = view_model
        self._inputs = FormInputs()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("920x760")
        self.minsize(820, 680)
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
        header.grid(row=0, column=0, padx=20, pady=(16, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            titles, text=APP_NAME, font=ctk.CTkFont(size=22, weight="bold")
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles,
            text="Genera los informes ODS insertando el contenido del Excel en el Word.",
            text_color=("gray40", "gray70"),
        ).pack(anchor="w")

        # Selector de tema (claro/oscuro/sistema).
        theme = ctk.CTkFrame(header, fg_color="transparent")
        theme.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(theme, text="Tema:").pack(side="left", padx=(0, 6))
        self._theme_menu = ctk.CTkOptionMenu(
            theme,
            values=["Sistema", "Claro", "Oscuro"],
            width=110,
            command=self._on_change_theme,
        )
        self._theme_menu.pack(side="left")

    @staticmethod
    def _on_change_theme(choice: str) -> None:
        ctk.set_appearance_mode({"Claro": "light", "Oscuro": "dark"}.get(choice, "system"))

    def _build_form(self) -> None:
        form = ctk.CTkFrame(self)
        form.grid(row=1, column=0, padx=20, pady=8, sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        self._word_selector = FileSelector(
            form, "Plantilla Word (.docx):", self._browse_word
        )
        self._word_selector.grid(row=0, column=0, padx=12, pady=(12, 2), sticky="ew")

        self._excel_selector = ExcelListSelector(form)
        self._excel_selector.grid(row=1, column=0, padx=12, pady=6, sticky="ew")

        self._output_selector = FileSelector(
            form, "Carpeta de salida:", self._browse_output
        )
        self._output_selector.grid(row=2, column=0, padx=12, pady=2, sticky="ew")

        month_row = ctk.CTkFrame(form, fg_color="transparent")
        month_row.grid(row=3, column=0, padx=12, pady=(2, 12), sticky="ew")
        ctk.CTkLabel(month_row, text="Mes a procesar:", width=160, anchor="w").pack(
            side="left", padx=(0, 8)
        )
        self._month_var = ctk.StringVar(value="")
        self._month_menu = ctk.CTkOptionMenu(
            month_row, values=list(self._vm.months), variable=self._month_var, width=200
        )
        self._month_menu.pack(side="left")

    def _build_console(self) -> None:
        self._progress = ProgressPanel(self)
        self._progress.grid(row=3, column=0, padx=20, pady=(8, 4), sticky="ew")

        self._console = ConsolePanel(self)
        self._console.grid(row=2, column=0, padx=20, pady=8, sticky="nsew")

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, padx=20, pady=(4, 16), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        self._start_button = ctk.CTkButton(
            footer, text="Iniciar", width=160, height=40, command=self._on_start
        )
        self._start_button.grid(row=0, column=1, padx=(0, 8))

        self._cancel_button = ctk.CTkButton(
            footer,
            text="Cancelar",
            width=140,
            height=40,
            fg_color="#b54b4b",
            hover_color="#9e3f3f",
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

        errors = self._vm.start(self._inputs, on_done=self._on_done)
        if errors:
            messagebox.showwarning("Faltan datos", "\n".join(errors))
            return

        self._set_running(True)
        self._poll()

    def _on_cancel(self) -> None:
        self._vm.cancel()
        self._console.append(EventLevel.WARNING, "Cancelación solicitada…")
        self._cancel_button.configure(state="disabled")

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

        textbox = ctk.CTkTextbox(self, wrap="word", font=("monospace", 12))
        textbox.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        textbox.insert("1.0", summary or "Sin resumen.")
        textbox.configure(state="disabled")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=1, column=0, pady=(0, 16))
        if output_path:
            ctk.CTkButton(
                buttons, text="Abrir carpeta de salida", command=self._open_output
            ).pack(side="left", padx=6)
        ctk.CTkButton(buttons, text="Cerrar", command=self.destroy).pack(side="left", padx=6)
        self.after(100, self.lift)

    def _open_output(self) -> None:
        folder = Path(self._output_path).parent if self._output_path else None
        if folder:
            open_path(folder)


def _short(path: str, max_len: int = 60) -> str:
    """Acorta una ruta larga para mostrarla."""
    return path if len(path) <= max_len else "…" + path[-(max_len - 1) :]
