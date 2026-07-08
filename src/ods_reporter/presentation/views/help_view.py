"""Módulo "Cómo usar": el manual de usuario dentro de la aplicación.

Reproduce el manual publicado en Notion con el lenguaje visual de la app:
una "página" desplazable con llamadas de atención (callouts), secciones,
pasos numerados y preguntas frecuentes. El contenido es estático y vive al
final de este módulo, de modo que actualizar el manual es editar texto.
"""

from __future__ import annotations

import customtkinter as ctk

from ods_reporter.presentation import theme
from ods_reporter.shared.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_EMPTY_ACTIVITY_TEXT,
    MIN_ACTIVITIES_THRESHOLD,
)

# Ancho de línea del texto: columna central estilo "página de documento".
_WRAP = 730


class HelpView(ctk.CTkFrame):
    """Vista del manual de usuario (módulo "Cómo usar")."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(
            self,
            fg_color=theme.CARD,
            corner_radius=12,
            border_width=1,
            border_color=theme.BORDER,
        )
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        scroll.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # Columna central de contenido (la "página").
        page = ctk.CTkFrame(scroll, fg_color="transparent")
        page.grid(row=0, column=0, padx=30, pady=(16, 30))
        page.grid_columnconfigure(0, weight=1)
        self._build_page(page)

    # --- Construcción de la página ---

    def _build_page(self, page: ctk.CTkFrame) -> None:
        row = 0
        ctk.CTkLabel(
            page,
            text=f"📖  Cómo usar {APP_NAME}",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=row, column=0, sticky="w")
        row += 1
        ctk.CTkLabel(
            page,
            text=f"Manual de usuario · versión {APP_VERSION}",
            text_color=theme.MUTED,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(0, 12))
        row += 1

        row = self._callout(
            page,
            row,
            "🌿",
            "No se necesitan conocimientos técnicos: si sabes elegir archivos y "
            "hacer clic, puedes generar el informe. Nada se escribe en el Word "
            "hasta que tú lo confirmes, y los archivos originales nunca se "
            "modifican.",
        )

        for section in _SECTIONS:
            row = self._heading(page, row, section.title)
            for block in section.blocks:
                row = block.render(self, page, row)

        ctk.CTkLabel(
            page,
            text=f"{APP_NAME} v{APP_VERSION}  ·  S.G.I. S.A.S. Consultoría e Ingeniería",
            text_color=theme.MUTED,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(26, 0))

    # --- Bloques visuales ---

    def _heading(self, page: ctk.CTkFrame, row: int, text: str) -> int:
        ctk.CTkLabel(
            page,
            text=text,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=theme.PRIMARY_DARK,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(20, 6))
        return row + 1

    def _callout(self, page: ctk.CTkFrame, row: int, icon: str, text: str) -> int:
        box = ctk.CTkFrame(page, fg_color=theme.CARD_INNER, corner_radius=10)
        box.grid(row=row, column=0, sticky="ew", pady=4)
        box.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(box, text=icon, font=ctk.CTkFont(size=16)).grid(
            row=0, column=0, padx=(12, 8), pady=10, sticky="n"
        )
        ctk.CTkLabel(
            box,
            text=text,
            wraplength=_WRAP - 60,
            justify="left",
            anchor="w",
        ).grid(row=0, column=1, padx=(0, 12), pady=10, sticky="w")
        return row + 1

    def _paragraph(self, page: ctk.CTkFrame, row: int, text: str) -> int:
        ctk.CTkLabel(
            page, text=text, wraplength=_WRAP, justify="left", anchor="w"
        ).grid(row=row, column=0, sticky="w", pady=2)
        return row + 1

    def _bullet(self, page: ctk.CTkFrame, row: int, title: str, text: str) -> int:
        line = ctk.CTkFrame(page, fg_color="transparent")
        line.grid(row=row, column=0, sticky="ew", pady=2)
        line.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(line, text="•", text_color=theme.PRIMARY, width=14).grid(
            row=0, column=0, sticky="nw"
        )
        content = ctk.CTkFrame(line, fg_color="transparent")
        content.grid(row=0, column=1, sticky="ew")
        if title:
            ctk.CTkLabel(
                content,
                text=title,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            ).pack(anchor="w")
        ctk.CTkLabel(
            content,
            text=text,
            wraplength=_WRAP - 30,
            justify="left",
            text_color=theme.TEXT if not title else theme.MUTED,
            anchor="w",
        ).pack(anchor="w")
        return row + 1

    def _step(self, page: ctk.CTkFrame, row: int, number: int, text: str) -> int:
        line = ctk.CTkFrame(page, fg_color="transparent")
        line.grid(row=row, column=0, sticky="ew", pady=3)
        line.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            line,
            text=str(number),
            width=26,
            height=26,
            corner_radius=13,
            fg_color=theme.PRIMARY,
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, padx=(0, 10), sticky="n")
        ctk.CTkLabel(
            line, text=text, wraplength=_WRAP - 40, justify="left", anchor="w"
        ).grid(row=0, column=1, sticky="w")
        return row + 1

    def _faq(self, page: ctk.CTkFrame, row: int, question: str, answer: str) -> int:
        box = ctk.CTkFrame(page, fg_color=theme.CARD_INNER, corner_radius=10)
        box.grid(row=row, column=0, sticky="ew", pady=3)
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            box,
            text=question,
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=_WRAP - 30,
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, padx=12, pady=(8, 0), sticky="w")
        ctk.CTkLabel(
            box,
            text=answer,
            text_color=theme.MUTED,
            wraplength=_WRAP - 30,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, padx=12, pady=(0, 8), sticky="w")
        return row + 1


# --- Contenido del manual (editar aquí, no en la interfaz) ---


class _Block:
    """Un bloque de contenido que sabe renderizarse en la página."""

    def __init__(self, kind: str, *args: object) -> None:
        self.kind = kind
        self.args = args

    def render(self, view: HelpView, page: ctk.CTkFrame, row: int) -> int:
        builder = {
            "p": view._paragraph,
            "bullet": view._bullet,
            "step": view._step,
            "callout": view._callout,
            "faq": view._faq,
        }[self.kind]
        return builder(page, row, *self.args)  # type: ignore[operator]


class _Section:
    def __init__(self, title: str, blocks: list[_Block]) -> None:
        self.title = title
        self.blocks = blocks


_SECTIONS: list[_Section] = [
    _Section(
        "Los módulos de la aplicación",
        [
            _Block(
                "bullet",
                "📝  Nuevo informe",
                "Aquí cargas los archivos y lanzas el análisis: la plantilla Word "
                "oficial, los Excel de los profesionales, la carpeta de salida y "
                "el mes. El carril derecho muestra el resumen de lo cargado.",
            ),
            _Block(
                "bullet",
                "📊  Resumen detallado",
                "Después de procesar, aquí revisas TODO antes de generar: qué "
                "recibirá cada actividad del Word, las advertencias y errores, la "
                "auditoría de profesionales y el contenido sin ubicación.",
            ),
            _Block(
                "bullet",
                "📖  Cómo usar",
                "Este manual, siempre disponible dentro de la aplicación.",
            ),
        ],
    ),
    _Section(
        "Generar un informe, paso a paso",
        [
            _Block(
                "step", 1,
                "En «Nuevo informe», pulsa Examinar y elige la plantilla Word "
                "oficial del informe (.docx). El original nunca se modifica.",
            ),
            _Block(
                "step", 2,
                "Agrega los reportes de todos los profesionales, en Excel (.xlsx, "
                ".xlsm) o en Word (.docx): «Agregar archivos» permite elegir varios "
                "a la vez y «Agregar carpeta» toma todos los de una carpeta. Los "
                "repetidos se ignoran automáticamente.",
            ),
            _Block(
                "step", 3,
                "Elige la carpeta de salida y el mes a procesar (la hoja del "
                "Excel que se leerá).",
            ),
            _Block(
                "step", 4,
                "Pulsa «PROCESAR Y REVISAR». La aplicación analiza todos los "
                "archivos sin escribir nada; el avance se ve en la consola.",
            ),
            _Block(
                "step", 5,
                "Pasarás automáticamente a «Resumen detallado». Revisa el estado "
                "de cada actividad, los contadores y la auditoría de la derecha.",
            ),
            _Block(
                "step", 6,
                "Si hay «contenido sin ubicación» (actividades del Excel que no "
                "existen en el Word), elige con el menú de cada una el numeral "
                "donde insertarla, o déjala sin insertar.",
            ),
            _Block(
                "step", 7,
                "Pulsa «GENERAR INFORME». Al terminar puedes abrir la carpeta de "
                "salida directamente desde la aplicación.",
            ),
        ],
    ),
    _Section(
        "El informe generado",
        [
            _Block(
                "bullet", "",
                "El informe queda en la carpeta elegida con el nombre de la "
                "plantilla más el mes (por ejemplo, «Informe ODS 123_JUNIO.docx»), "
                "junto a un archivo «_reporte.txt» con el resumen completo.",
            ),
            _Block(
                "bullet", "",
                f"Las actividades que ningún profesional diligenció quedan con el "
                f"texto institucional: «{DEFAULT_EMPTY_ACTIVITY_TEXT}».",
            ),
            _Block(
                "bullet", "",
                "Las filas de «OTRAS ACTIVIDADES SOLICITADAS POR…» del Excel se "
                "insertan, con su fecha, en la fila de «Observaciones generales "
                "y/o actividades adicionales» del Word.",
            ),
        ],
    ),
    _Section(
        "Validaciones que te protegen",
        [
            _Block(
                "bullet", "",
                "Si un Excel pertenece a OTRA ODS (número distinto o actividades "
                "que no coinciden con la plantilla), el archivo se rechaza "
                "completo y queda registrado en los errores: nunca se mezcla "
                "contenido de dos contratos.",
            ),
            _Block(
                "bullet", "",
                "Si el enunciado de una actividad no coincide con el de la "
                "plantilla, aparece una advertencia con el porcentaje de "
                "similitud, el profesional y el archivo de origen.",
            ),
            _Block(
                "bullet", "",
                f"La auditoría señala a los profesionales sin actividades y a los "
                f"que reportaron menos de {MIN_ACTIVITIES_THRESHOLD}, para "
                f"seguimiento.",
            ),
            _Block(
                "bullet", "",
                "Si un Excel no se puede leer, los demás continúan; el error "
                "indica siempre el archivo culpable.",
            ),
        ],
    ),
    _Section(
        "Preguntas frecuentes",
        [
            _Block(
                "faq",
                "¿El programa modifica mis Excel o la plantilla Word?",
                "No. Los Excel se abren solo para lectura y la plantilla se "
                "copia: el informe se genera sobre la copia.",
            ),
            _Block(
                "faq",
                "¿Mis datos se suben a internet?",
                "No. La aplicación funciona completamente sin conexión; no envía "
                "ni recibe nada de internet.",
            ),
            _Block(
                "faq",
                "¿Puedo cargar el informe Word de un profesional en vez del Excel?",
                "Sí. Los .docx con la misma tabla de actividades se leen igual "
                "que los Excel: las actividades se emparejan por su enunciado "
                "(aunque el numeral cambie) y lo que no coincida queda como "
                "«contenido sin ubicación» para que tú decidas su destino.",
            ),
            _Block(
                "faq",
                "¿Puedo cancelar un procesamiento en curso?",
                "Sí, con el botón Cancelar. Se detiene de forma segura y no deja "
                "archivos a medias.",
            ),
            _Block(
                "faq",
                "¿Cómo actualizo a una versión nueva?",
                "Instala la versión nueva con su instalador: reemplaza a la "
                "anterior automáticamente, conservando el acceso directo.",
            ),
            _Block(
                "faq",
                "¿Dónde están los registros para soporte técnico?",
                "En %LOCALAPPDATA%\\ODS Reporter\\logs\\ods_reporter.log. Solo "
                "contienen eventos técnicos, nunca el contenido de los informes.",
            ),
        ],
    ),
]
