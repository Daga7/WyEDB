"""Identidad visual de la aplicación (estilo empresarial verde S.G.I.).

Paleta inspirada en la referencia de diseño: verde bosque como color primario
(acciones, estados de éxito), superficies blancas con bordes suaves sobre un
fondo gris-verdoso claro, y acentos ámbar/rojo para advertencias y errores.
Único punto de verdad de los colores: todas las vistas importan de aquí.

Los pares ``(claro, oscuro)`` siguen la convención de CustomTkinter: el primer
valor aplica en tema claro y el segundo en tema oscuro.
"""

from __future__ import annotations

from typing import Final

# --- Color primario (verde bosque) ---
PRIMARY: Final[str] = "#15803D"
PRIMARY_HOVER: Final[str] = "#116936"
PRIMARY_DARK: Final[str] = "#14532D"

# Alias usados por acciones de generación/éxito (mismo verde corporativo).
GREEN: Final[str] = PRIMARY
GREEN_HOVER: Final[str] = PRIMARY_HOVER

# --- Estados ---
WARNING: Final[str] = "#B45309"
DANGER: Final[str] = "#C2453D"
DANGER_HOVER: Final[str] = "#A33830"

# --- Superficies ---
BG: Final[tuple[str, str]] = ("#F3F5F3", "#141917")          # fondo de la ventana
SIDEBAR: Final[tuple[str, str]] = ("#FFFFFF", "#1A201C")     # barra lateral
CARD: Final[tuple[str, str]] = ("#FFFFFF", "#1D2420")        # tarjetas
CARD_INNER: Final[tuple[str, str]] = ("#F4F6F4", "#262E29")  # campos/listas dentro
BORDER: Final[tuple[str, str]] = ("#E2E8E3", "#2E3730")      # borde de tarjetas

# --- Texto ---
MUTED: Final[tuple[str, str]] = ("gray40", "gray65")
TEXT: Final[tuple[str, str]] = ("gray10", "gray90")

# --- Botones secundarios ---
SECONDARY: Final[tuple[str, str]] = ("#ECF0EC", "#2A322C")
SECONDARY_HOVER: Final[tuple[str, str]] = ("#E0E6E0", "#333D36")
TEXT_ON_SECONDARY: Final[tuple[str, str]] = ("gray12", "gray90")

# --- Chips de estado (p. ej. "Válido" en la lista de Excel) ---
SUCCESS_CHIP_BG: Final[tuple[str, str]] = ("#E7F4EB", "#1E3527")
SUCCESS_CHIP_TEXT: Final[tuple[str, str]] = ("#15803D", "#7FC98B")
WARNING_CHIP_BG: Final[tuple[str, str]] = ("#FBF0DE", "#3B2E17")
WARNING_CHIP_TEXT: Final[tuple[str, str]] = ("#B45309", "#E0A75E")

# --- Stepper (pasos del flujo) ---
STEP_PENDING_BG: Final[tuple[str, str]] = ("#EAEEEA", "#2A322C")
STEP_PENDING_TEXT: Final[tuple[str, str]] = ("gray45", "gray60")

# Consola: fondo oscuro fijo (en ambos temas) para que los colores por severidad
# se lean siempre igual, estilo terminal. El texto por defecto DEBE fijarse claro
# explícitamente: en tema claro el color de texto por defecto es casi negro y
# resultaría invisible sobre este fondo.
CONSOLE_BG: Final[str] = "#171C1A"
CONSOLE_TEXT: Final[str] = "#DCE3EA"
