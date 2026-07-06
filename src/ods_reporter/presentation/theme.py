"""Identidad visual de la aplicación (paleta S.G.I.).

Azul corporativo (el fondo del logo) como color primario y verde (la hoja del
logo, guiño ambiental) para acciones de generación, éxito y progreso, sobre
superficies neutras y planas. Único punto de verdad de los colores: todas las
vistas importan de aquí para mantener la coherencia.

Los pares ``(claro, oscuro)`` siguen la convención de CustomTkinter: el primer
valor aplica en tema claro y el segundo en tema oscuro.
"""

from __future__ import annotations

from typing import Final

# --- Marca S.G.I. ---
PRIMARY: Final[str] = "#14527A"          # azul del logo
PRIMARY_HOVER: Final[str] = "#0E3D5C"
GREEN: Final[str] = "#4F9D45"            # verde hoja (acción de generar / éxito)
GREEN_HOVER: Final[str] = "#3F7F37"
DANGER: Final[str] = "#B04A4A"
DANGER_HOVER: Final[str] = "#933D3D"

# --- Superficies y texto ---
CARD: Final[tuple[str, str]] = ("gray96", "gray14")         # tarjeta principal
CARD_INNER: Final[tuple[str, str]] = ("gray90", "gray19")   # campos/listas dentro
MUTED: Final[tuple[str, str]] = ("gray40", "gray65")        # texto secundario
SECONDARY: Final[tuple[str, str]] = ("gray86", "gray27")    # botones secundarios
SECONDARY_HOVER: Final[tuple[str, str]] = ("gray79", "gray32")
TEXT_ON_SECONDARY: Final[tuple[str, str]] = ("gray12", "gray90")

# Consola: fondo oscuro fijo (en ambos temas) para que los colores por severidad
# se lean siempre igual, estilo terminal. El texto por defecto DEBE fijarse claro
# explícitamente: en tema claro el color de texto por defecto es casi negro y
# resultaría invisible sobre este fondo.
CONSOLE_BG: Final[str] = "#171C22"
CONSOLE_TEXT: Final[str] = "#DCE3EA"
