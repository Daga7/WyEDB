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


def load_decoration(
    filename: str, *, width: int, radius: int = 14
) -> ctk.CTkImage | None:
    """Imagen decorativa con esquinas redondeadas, o ``None`` si no existe.

    Redondea las esquinas sobre una copia a 2x y la muestra reducida, para que
    el borde quede nítido y la imagen se integre con las tarjetas de la
    interfaz en vez de verse "pegada".
    """
    path = resource_path(f"assets/{filename}")
    if not path.exists():
        return None
    try:
        from PIL import Image, ImageDraw

        image = Image.open(path).convert("RGBA")
        height = max(1, int(width * image.height / image.width))
        doubled = image.resize((width * 2, height * 2), Image.LANCZOS)
        mask = Image.new("L", doubled.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, doubled.width, doubled.height), radius * 2, fill=255
        )
        doubled.putalpha(mask)
        return ctk.CTkImage(light_image=doubled, dark_image=doubled, size=(width, height))
    except Exception:  # noqa: BLE001 - una decoración nunca debe tumbar la ventana
        return None
