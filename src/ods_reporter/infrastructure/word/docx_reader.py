"""Lector de la estructura de actividades de un documento Word de ODS.

Localiza la tabla de actividades y extrae, por cada actividad, sus entregables
(sub-filas) junto con la **ubicación exacta** donde se debe insertar el contenido
(la celda y el párrafo "Descripción de las actividades realizadas:").

Devuelve descriptores que conservan referencias vivas a los objetos de
python-docx, de modo que el escritor (``docx_writer``) pueda insertar después.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from docx.oxml.ns import qn
from docx.table import _Cell

from ods_reporter.domain.exceptions import WordProcessError
from ods_reporter.infrastructure.matching.roman_numerals import roman_to_int
from ods_reporter.shared.text_utils import normalize_text

if TYPE_CHECKING:
    from docx.document import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

# Encabezados de la tabla de actividades (normalizados).
_TABLE_HEADER_NO = "no"
_TABLE_HEADER_ACTIVITIES = "actividades"

# Marcadores de sección dentro de la celda de una actividad (normalizados).
_MARKER_ACTIVITY = "actividad:"
_MARKER_ENTREGABLE = "descripcion del entregable:"
_MARKER_REALIZADAS = "descripcion de las actividades realizadas:"

# Inicio (normalizado) de la fila de observaciones/actividades adicionales, que
# aparece tras la última actividad ("Observaciones generales y/o actividades
# adicionales encomendadas por...").
_MARKER_OBSERVACIONES = "observaciones"


@dataclass(slots=True)
class WordEntregable:
    """Un entregable del Word con la ubicación donde insertar su contenido.

    Attributes
    ----------
    entregable_text:
        Texto del entregable (para alinear con el Excel).
    cell:
        Celda de la tabla que contiene este entregable.
    slot_paragraph:
        Párrafo-plantilla (la viñeta ``List Paragraph`` del entregable) que se usa
        para clonar el formato e insertar el contenido.
    """

    entregable_text: str
    cell: _Cell
    slot_paragraph: Paragraph

    @property
    def normalized_text(self) -> str:
        return normalize_text(self.entregable_text)


@dataclass(slots=True)
class WordActivity:
    """Una actividad del Word: su numeral y sus entregables."""

    ordinal: int
    label: str
    entregables: list[WordEntregable] = field(default_factory=list)


@dataclass(slots=True)
class WordStructure:
    """Estructura completa del documento: actividades + sección de observaciones."""

    activities: list[WordActivity] = field(default_factory=list)
    observaciones: WordEntregable | None = None


class DocxReader:
    """Extrae la estructura de actividades de un documento Word."""

    def read_structure(self, document: Document) -> WordStructure:
        """Devuelve las actividades y la sección de observaciones (si existe).

        Raises
        ------
        WordProcessError
            Si no se encuentra la tabla de actividades.
        """
        table = self._find_activities_table(document)
        structure = WordStructure()
        current: WordActivity | None = None

        # Se itera a nivel XML (cada <w:tr> tiene sus propias <w:tc>): con celdas
        # combinadas verticalmente, ``row.cells`` de python-docx desplaza columnas.
        for tr in table._tbl.tr_lst[1:]:  # se omite el encabezado
            tcs = tr.tc_lst
            if len(tcs) < 2:
                continue
            col_no = _Cell(tcs[0], table)
            col_activity = _Cell(tcs[1], table)

            ordinal = self._read_ordinal(col_no)

            # Fila de observaciones/actividades adicionales: cierra la lista de
            # actividades (su celda de texto es la PRIMERA de la fila).
            if ordinal is None and self._is_observaciones_cell(col_no):
                structure.observaciones = self._read_observaciones(col_no)
                current = None
                continue

            entregable = self._read_entregable(col_activity)

            if ordinal is not None and (current is None or ordinal != current.ordinal):
                current = WordActivity(ordinal=ordinal, label=self._read_label(col_activity))
                structure.activities.append(current)

            if current is not None and entregable is not None:
                current.entregables.append(entregable)

        return structure

    def read_activities(self, document: Document) -> list[WordActivity]:
        """Devuelve solo las actividades (compatibilidad con el uso existente)."""
        return self.read_structure(document).activities

    # --- Sección de observaciones ---

    @staticmethod
    def _is_observaciones_cell(cell: _Cell) -> bool:
        return normalize_text(cell.text).startswith(_MARKER_OBSERVACIONES)

    def _read_observaciones(self, cell: _Cell) -> WordEntregable | None:
        """Extrae la sección de observaciones: título + viñeta de inserción."""
        slot = self._find_slot(cell.paragraphs, None)
        if slot is None:
            return None
        return WordEntregable(
            entregable_text=_first_title_text(cell.paragraphs), cell=cell, slot_paragraph=slot
        )

    # --- Localización de la tabla ---

    @staticmethod
    def _find_activities_table(document: Document) -> Table:
        for table in document.tables:
            if not table.rows:
                continue
            header = table.rows[0].cells
            if len(header) < 2:
                continue
            col0 = normalize_text(header[0].text)
            col1 = normalize_text(header[1].text)
            if col0 == _TABLE_HEADER_NO and col1 == _TABLE_HEADER_ACTIVITIES:
                return table
        raise WordProcessError(
            "No se encontró la tabla de actividades (encabezado 'No' / 'Actividades')."
        )

    # --- Lectura de celdas ---

    @staticmethod
    def _read_ordinal(cell: _Cell) -> int | None:
        """Lee el numeral del 'No': admite romanos (I, II) y arábigos (1, 2)."""
        text = cell.text.strip()
        roman = roman_to_int(text)
        if roman is not None:
            return roman
        try:
            number = int(float(text))
        except (ValueError, TypeError):
            return None
        return number if number > 0 else None

    @staticmethod
    def _read_label(cell: _Cell) -> str:
        paragraphs = cell.paragraphs
        idx = _find_marker(paragraphs, _MARKER_ACTIVITY)
        if idx is not None:
            return _text_until_next_marker(paragraphs, idx)
        # Plantillas sin el marcador "Actividad:": el título es el primer texto.
        return _first_title_text(paragraphs)

    def _read_entregable(self, cell: _Cell) -> WordEntregable | None:
        """Extrae un entregable de la celda, soportando dos formatos de plantilla:

        - Con marcadores ("Descripción del entregable:" / "...realizadas:").
        - Sin marcadores: el título de la actividad y, debajo, las viñetas.

        En ambos casos el slot de inserción es la primera viñeta (``List Paragraph``).
        """
        paragraphs = cell.paragraphs
        entregable_idx = _find_marker(paragraphs, _MARKER_ENTREGABLE)
        realizadas_idx = _find_marker(paragraphs, _MARKER_REALIZADAS)

        slot = self._find_slot(paragraphs, realizadas_idx)
        if slot is None:
            return None  # sin viñeta no hay dónde insertar: no es celda de contenido

        if entregable_idx is not None:
            entregable_text = _text_until_next_marker(paragraphs, entregable_idx)
        else:
            # Sin marcador de entregable: se usa el título de la actividad como clave.
            entregable_text = _first_title_text(paragraphs)

        return WordEntregable(entregable_text=entregable_text, cell=cell, slot_paragraph=slot)

    @staticmethod
    def _find_slot(paragraphs: list[Paragraph], realizadas_idx: int | None) -> Paragraph | None:
        """Localiza el slot de inserción: la viñeta de plantilla (``List Paragraph``).

        Robusto ante plantillas donde, en algunas sub-filas, falta el encabezado
        "Descripción de las actividades realizadas:": en ese caso el slot es
        igualmente la primera viñeta que sigue al entregable.
        """
        start = realizadas_idx + 1 if realizadas_idx is not None else 0
        for paragraph in paragraphs[start:]:
            if _is_list_paragraph(paragraph):
                return paragraph
        # Respaldos: cualquier viñeta de la celda, o el párrafo tras el encabezado.
        for paragraph in paragraphs:
            if _is_list_paragraph(paragraph):
                return paragraph
        if realizadas_idx is not None and realizadas_idx + 1 < len(paragraphs):
            return paragraphs[realizadas_idx + 1]
        return None


# --- Utilidades de párrafos ---

def _first_title_text(paragraphs: list[Paragraph]) -> str:
    """Primer texto que no es viñeta ni un encabezado de sección conocido.

    En plantillas sin marcadores, corresponde al título de la actividad.
    """
    markers = (_MARKER_ACTIVITY, _MARKER_ENTREGABLE, _MARKER_REALIZADAS)
    for paragraph in paragraphs:
        if _is_list_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        if not text:
            continue
        if any(normalize_text(text).startswith(marker) for marker in markers):
            continue
        return text
    return ""


def _is_list_paragraph(paragraph: Paragraph) -> bool:
    """``True`` si el párrafo es una viñeta de lista (por estilo o por numeración).

    Se comprueba el nombre del estilo (tolerante a idioma: "List Paragraph" /
    "Párrafo de lista") y, como señal fuerte, la presencia de ``numPr`` en el XML.
    """
    name = normalize_text(paragraph.style.name or "")
    if "list" in name or "lista" in name:
        return True
    p_pr = paragraph._p.find(qn("w:pPr"))
    return p_pr is not None and p_pr.find(qn("w:numPr")) is not None


def _find_marker(paragraphs: list[Paragraph], marker: str) -> int | None:
    for i, paragraph in enumerate(paragraphs):
        if normalize_text(paragraph.text).startswith(marker):
            return i
    return None


def _text_until_next_marker(paragraphs: list[Paragraph], start: int) -> str:
    """Texto entre el marcador en ``start`` y el siguiente marcador conocido.

    Incluye lo que venga tras los dos puntos del propio marcador (si lo hay) y los
    párrafos siguientes hasta encontrar otro encabezado de sección.
    """
    markers = (_MARKER_ACTIVITY, _MARKER_ENTREGABLE, _MARKER_REALIZADAS)
    pieces: list[str] = []

    first = paragraphs[start].text
    if ":" in first:
        after_colon = first.split(":", 1)[1].strip()
        if after_colon:
            pieces.append(after_colon)

    for paragraph in paragraphs[start + 1 :]:
        normalized = normalize_text(paragraph.text)
        if any(normalized.startswith(m) for m in markers):
            break
        text = paragraph.text.strip()
        if text:
            pieces.append(text)

    return " ".join(pieces).strip()
