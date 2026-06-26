"""Utilidades de normalización de texto (puras y reutilizables).

Se usan para comparar nombres de actividades de forma robusta (sin que afecten
tildes, mayúsculas o espacios sobrantes) y para quitar numeraciones iniciales.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")

# Numeración inicial a eliminar: arábiga (1, 10), romana (i, ii, iv) o una sola
# letra (a, b), seguida de un separador (. ) - :).
#   "i. Identificar..."   -> "Identificar..."
#   "1) Cargar..."        -> "Cargar..."
#   "vii. Elaborar..."    -> "Elaborar..."
_LEADING_NUMERAL_RE = re.compile(
    r"^\s*(?:\d+|[ivxlcdm]+|[a-z])\s*[.)\-:]\s*",
    re.IGNORECASE,
)

# Viñeta inicial sin numeral: un guion o símbolo de lista seguido de espacio.
#   "- Radicación ICA"  -> "Radicación ICA"
#   "• Seguimiento"     -> "Seguimiento"
_LEADING_BULLET_RE = re.compile(r"^\s*[-–—•*·]+\s+")


def strip_accents(text: str) -> str:
    """Elimina tildes y diacríticos, conservando la letra base ('á' -> 'a')."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def collapse_whitespace(text: str) -> str:
    """Reduce cualquier secuencia de espacios/tabs/saltos a un único espacio."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_text(text: str) -> str:
    """Devuelve una forma canónica para comparar: sin tildes, en minúsculas y
    con los espacios normalizados.

    Ejemplo: ``"  Educación  Ambiental "`` -> ``"educacion ambiental"``.
    """
    return collapse_whitespace(strip_accents(text)).lower()


def strip_leading_numeral(text: str) -> str:
    """Quita una única numeración inicial del texto, si existe.

    Ejemplos:
        ``"i. Identificar y analizar"`` -> ``"Identificar y analizar"``
        ``"1) Cargar soporte"``         -> ``"Cargar soporte"``
        ``"Sin numeral"``               -> ``"Sin numeral"``
    """
    return _LEADING_NUMERAL_RE.sub("", text, count=1).strip()


def strip_leading_bullet(text: str) -> str:
    """Quita una viñeta inicial (guion o símbolo de lista), si existe.

    Ejemplos:
        ``"- Radicación ICA"`` -> ``"Radicación ICA"``
        ``"• Seguimiento"``    -> ``"Seguimiento"``
    """
    return _LEADING_BULLET_RE.sub("", text, count=1).strip()


# Caracteres de marcador de posición de un slot "vacío" (guion, punto, viñeta...).
_PLACEHOLDER_CHARS = set(".-·•–—­ \t")


def is_blank_or_placeholder(text: str) -> bool:
    """``True`` si el texto está vacío o solo contiene marcadores de posición.

    Trata como "vacío" los slots de plantilla que traen un guion, un punto o una
    viñeta sueltos (p. ej. ``"-"``, ``".  "``), no solo los completamente vacíos.
    """
    stripped = text.strip()
    return stripped == "" or all(char in _PLACEHOLDER_CHARS for char in stripped)


def clean_content_line(text: str) -> str:
    """Limpia una línea de contenido: quita numeración o viñeta inicial y espacios.

    No altera el texto interno (mayúsculas, tildes, puntuación): solo retira el
    prefijo de lista para que luego se inserte con un guion uniforme en el Word.
    """
    stripped = text.strip()
    without_numeral = strip_leading_numeral(stripped)
    return strip_leading_bullet(without_numeral)
