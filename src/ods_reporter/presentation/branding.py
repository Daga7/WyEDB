"""Identidad visual en las ventanas: icono de la barra de título y logo.

Separado de las vistas para que cualquier ventana (principal o diálogos) lo
aplique con una llamada. Nunca lanza: si falta un recurso o el sistema no
soporta la operación, la ventana simplemente queda sin icono/logo.
"""

from __future__ import annotations

import sys
import tkinter as tk

import customtkinter as ctk

from ods_reporter.shared.resources import resource_path

# CustomTkinter aplica su icono por defecto con un retraso (~250 ms) tras crear
# la ventana, pisando el nuestro; se reaplica después de ese momento.
_ICON_REAPPLY_MS = 350


def apply_window_icon(window: ctk.CTk | ctk.CTkToplevel) -> None:
    """Pone el icono S.G.I. en la barra de título y la barra de tareas."""

    def _apply() -> None:
        try:
            ico = resource_path("assets/icon.ico")
            png = resource_path("assets/icon.png")
            if sys.platform.startswith("win") and ico.exists():
                window.iconbitmap(str(ico))
            elif png.exists():
                window.iconphoto(True, tk.PhotoImage(file=str(png)))
        except Exception:  # noqa: BLE001 - el icono nunca debe tumbar la ventana
            pass

    _apply()
    window.after(_ICON_REAPPLY_MS, _apply)


def load_logo(height: int = 40) -> ctk.CTkImage | None:
    """Logo S.G.I. como imagen para la cabecera, o ``None`` si no está disponible."""
    path = resource_path("assets/logo.png")
    if not path.exists():
        return None
    try:
        from PIL import Image

        image = Image.open(path)
        width = int(height * image.width / image.height)
        return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))
    except Exception:  # noqa: BLE001 - sin Pillow o imagen dañada: seguir sin logo
        return None
