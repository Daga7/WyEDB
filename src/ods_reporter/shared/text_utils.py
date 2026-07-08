"""Utilidades de normalización de texto (puras y reutilizables).

Se usan para comparar nombres de actividades de forma robusta (sin que afecten
tildes, mayúsculas o espacios sobrantes) y para quitar numeraciones iniciales.
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")

# Numeración inicial a eliminar: arábiga (1, 10), romana (i, ii, iv) o una sola
# letra (a, b), seguida de un separador (. ) - : _).
#   "i. Identificar..."   -> "Identificar..."
#   "1) Cargar..."        -> "Cargar..."
#   "vii. Elaborar..."    -> "Elaborar..."
#   "7_Instalación..."    -> "Instalación..." (numeración con guion bajo)
_LEADING_NUMERAL_RE = re.compile(
    r"^\s*(?:\d+|[ivxlcdm]+|[a-z])\s*[.)\-:_]\s*",
    re.IGNORECASE,
)

# Numeral inicial SIN separador de puntuación, seguido solo de espacios.
# Cubre etiquetas reales tipo "xiii   Acompañar…" o "13  Elaborar…" (con espacios
# duros \xa0), donde el numeral no lleva punto. Se limita a números arábigos y a
# romanos (>=1 carácter romano), NUNCA a una sola letra suelta, para no borrar
# palabras reales como "a continuación". Exige >=2 espacios o un espacio duro como
# separador, señal de que es una numeración y no la primera palabra del texto.
_LEADING_NUMERAL_NOSEP_RE = re.compile(
    r"^\s*(?:\d+|[ivxlcdm]+)(?:\xa0+|\s{2,})",
    re.IGNORECASE,
)

# Viñeta/separador inicial sin numeral: guion, asterisco, círculo, guion bajo u
# otro símbolo de lista. Real en los Excel de los profesionales: el separador más
# común es "_" (guion bajo), seguido de "- ", "•", "*".
#   "- Radicación ICA"  -> "Radicación ICA"
#   "• Seguimiento"     -> "Seguimiento"
#   "○ Círculo"         -> "Círculo"
#   "_Gestión"          -> "Gestión"
#   "_ Se elabora"      -> "Se elabora"
# Nota: NO se incluyen '(' ni '"' porque suelen ser parte real del contenido
# (p. ej. '(DIR)', 'informe "BALANCE ODS"'). El espacio final es opcional para
# cubrir el caso pegado ("_Gestión") sin exigir separador.
_BULLET_CHARS = r"-–—•*·◦○●∙▪▫‣º°+~_"
_LEADING_BULLET_RE = re.compile(rf"^\s*[{_BULLET_CHARS}]+\s*")

# Número "pelado" inicial (sin punto ni paréntesis): "1 ", "12 ".
# Se usa SOLO cuando el contexto indica una lista numerada (ver ContentNormalizer),
# para no borrar números que son parte real del contenido (p. ej. "3 ICA radicados").
_LEADING_BARE_NUMBER_RE = re.compile(r"^\s*\d{1,2}\s+")


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
        ``"xiii   Acompañar"``          -> ``"Acompañar"`` (numeral sin punto)
        ``"Sin numeral"``               -> ``"Sin numeral"``
    """
    without = _LEADING_NUMERAL_RE.sub("", text, count=1)
    if without == text:
        # No había numeral con separador de puntuación; probamos el numeral
        # "pelado" seguido solo de espacios (romano/arábigo + espacios/duros).
        without = _LEADING_NUMERAL_NOSEP_RE.sub("", text, count=1)
    return without.strip()


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


def strip_leading_bare_number(text: str) -> str:
    """Quita un número inicial "pelado" (sin punto ni paréntesis): ``"1 Cargar"`` -> ``"Cargar"``."""
    return _LEADING_BARE_NUMBER_RE.sub("", text, count=1).strip()


# Número de ODS dentro de un texto: "3040727 ECP ODS No. 11" -> "11".
# Tolera variantes: "ODS 11", "ODS N° 11", "ODS Nro. 11", "ODS No: 11".
_ODS_NUMBER_RE = re.compile(
    r"\bODS\s*(?:N(?:ro|o)?\s*[°ºª]?\s*[.:]?\s*)?(\d+)",
    re.IGNORECASE,
)


def extract_ods_number(text: str) -> str:
    """Extrae el número de ODS de un texto, o ``''`` si no hay uno reconocible."""
    match = _ODS_NUMBER_RE.search(text or "")
    return match.group(1) if match else ""


def clean_content_line(text: str) -> str:
    """Limpia una línea de contenido: quita numeración/viñetas iniciales y colapsa espacios.

    Aplica la regla del punto 2 del negocio: tras cada salto de línea (esta función
    se llama por línea) se elimina cualquier prefijo de lista/separador que no sea
    texto real —``-``, ``*``, ``•``, ``○``, ``_``, ``1.``, ``1)``, ``a.``, ``i.``…—
    y se reducen los espacios sobrantes. Se hace de forma **repetida** para cubrir
    combinaciones reales (``"_- "``, ``"1. - "``, ``"__"``), deteniéndose en cuanto
    empieza el texto.

    No se tocan ``(`` ni ``"`` (suelen ser parte real del contenido), ni el resto
    del texto (mayúsculas, tildes, puntuación). El número "pelado" (``1 ``) lo
    gestiona el normalizador, que sabe si la celda es una lista numerada.
    """
    result = collapse_whitespace(text)
    # Quita capas de numeral/viñeta hasta que no reste ninguno (o quede vacío).
    while result:
        stripped = strip_leading_bullet(strip_leading_numeral(result))
        if stripped == result:
            break
        result = stripped
    return result
