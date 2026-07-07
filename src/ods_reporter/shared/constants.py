"""Constantes y reglas de negocio fijas de la aplicación.

Centralizar estos valores aquí evita "números mágicos" dispersos y facilita
ajustarlos en un único lugar si el negocio cambia.
"""

from __future__ import annotations

from typing import Final

# --- Identidad de la aplicación ---
APP_NAME: Final[str] = "ODS Reporter"
APP_VERSION: Final[str] = "3.1.1"

# --- Meses del año (nombres de las pestañas del Excel, en mayúsculas) ---
MONTHS: Final[tuple[str, ...]] = (
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
)

# --- Reglas de negocio ---

# Texto que se inserta en una actividad cuando NINGÚN profesional la diligenció.
DEFAULT_EMPTY_ACTIVITY_TEXT: Final[str] = (
    "Durante el periodo se estuvo atento a cualquier solicitud "
    "pero no se requirió el servicio"
)

# Contenido de la columna F que se considera "sin actividad" (se ignora).
# Todo se compara de forma NORMALIZADA (sin tildes, minúsculas, sin espacios
# sobrantes y sin puntuación final).
#
# - Prefijos de frase: basta con que el texto EMPIECE así (tolera variaciones de
#   redacción al final, como "...para el periodo reportado").
NO_ACTIVITY_SENTENCE_PREFIXES: Final[tuple[str, ...]] = (
    "no se requirio esta actividad",
    "no se requirio el servicio",
    "no se presento actividad",
)
# - Marcadores exactos: deben coincidir por completo (evita falsos positivos como
#   "no aplica para enero pero se hizo X").
NO_ACTIVITY_EXACT_MARKERS: Final[tuple[str, ...]] = (
    "no aplica",
    "n/a",
    "na",
)
# - Frases contenidas: si el texto las CONTIENE (en cualquier posición) significa
#   que no se realizó la actividad, aunque venga precedido de "Durante el periodo..."
#   o "En el presente periodo...". También cubre el cierre típico
#   "...sin embargo, se estuvo presto a solicitudes".
# Raíces deliberadamente cortas para cubrir variantes de redacción y erratas
# reales ("no fue requerida/requerido/requerdida", "no se requirió el servicio/
# producto/esta actividad", etc.).
NO_ACTIVITY_CONTAINS: Final[tuple[str, ...]] = (
    "no se requirio",          # ...el servicio / el producto / esta actividad
    "no fue requer",           # no fue requerida / requerido / requerdida (errata)
    "no fue requir",           # no fue requerido / requirerido (erratas)
    "no se aplico este recurso",
    "no se presto el servicio",
    "no se presento actividad",
)

# Umbral por debajo del cual un profesional se marca para seguimiento.
MIN_ACTIVITIES_THRESHOLD: Final[int] = 5

# Carácter usado como viñeta al insertar ítems en el Word.
BULLET_PREFIX: Final[str] = "- "

# --- Rutas / archivos ---
LOG_DIR_NAME: Final[str] = "logs"
LOG_FILE_NAME: Final[str] = "ods_reporter.log"

# --- Extensiones válidas ---
EXCEL_EXTENSIONS: Final[tuple[str, ...]] = (".xlsx", ".xlsm")
WORD_EXTENSIONS: Final[tuple[str, ...]] = (".docx",)
