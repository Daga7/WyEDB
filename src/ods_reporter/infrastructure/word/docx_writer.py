"""Escritor que inserta contenido en los slots de un documento Word.

Objetivo crítico: **conservar el formato al 100%**. Para ello, en lugar de crear
párrafos desde cero, se **clona** el párrafo-slot existente (el ``List Paragraph``
vacío que sigue al encabezado "Descripción de las actividades realizadas:") y solo
se le cambia el texto. Así se preservan estilo, viñeta, nivel de lista, fuente,
tamaño y demás propiedades, exactamente como si lo hubiera escrito una persona.

No se toca ningún otro párrafo, tabla, imagen ni estilo del documento.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from docx.text.paragraph import Paragraph

from ods_reporter.domain.value_objects.content_item import ContentItem
from ods_reporter.shared.text_utils import is_blank_or_placeholder

if TYPE_CHECKING:
    from ods_reporter.infrastructure.word.docx_reader import WordEntregable


class DocxWriter:
    """Inserta ítems de contenido en los entregables del Word."""

    def fill_entregable(
        self, entregable: WordEntregable, items: tuple[ContentItem, ...]
    ) -> int:
        """Inserta ``items`` como viñetas en el slot del entregable.

        Reemplaza el slot vacío de plantilla por el primer ítem y añade el resto
        a continuación, clonando el formato. Devuelve la cantidad de ítems escritos.

        Si ``items`` está vacío, no hace nada (el llenado por defecto se decide
        en la capa superior, Fase 8).
        """
        if not items:
            return 0

        template = self._resolve_template_paragraph(entregable)

        # El primer ítem reutiliza el párrafo-slot de plantilla (si está vacío);
        # si el slot ya tenía contenido, se inserta uno nuevo después.
        if self._is_blank(template):
            self._set_text(template, items[0].text)
            anchor = template
            rest = items[1:]
        else:
            anchor = self._clone_after(template, items[0].text)
            rest = items[1:]

        for item in rest:
            anchor = self._clone_after(anchor, item.text)

        return len(items)

    def set_default_text(self, entregable: WordEntregable, text: str) -> None:
        """Escribe el texto por defecto en el slot vacío del entregable."""
        template = self._resolve_template_paragraph(entregable)
        if self._is_blank(template):
            self._set_text(template, text)
        else:
            self._clone_after(template, text)

    # --- Internos ---

    @staticmethod
    def _resolve_template_paragraph(entregable: WordEntregable) -> Paragraph:
        """Devuelve el párrafo-plantilla (viñeta) donde se inserta el contenido."""
        return entregable.slot_paragraph

    @staticmethod
    def _is_blank(paragraph: Paragraph) -> bool:
        return is_blank_or_placeholder(paragraph.text)

    @staticmethod
    def _set_text(paragraph: Paragraph, text: str) -> None:
        """Fija el texto del párrafo conservando el formato del primer run.

        Reutiliza el primer run (su fuente/estilo) y elimina los runs sobrantes,
        de modo que el formato de carácter del slot se preserve.
        """
        if paragraph.runs:
            paragraph.runs[0].text = text
            for extra_run in paragraph.runs[1:]:
                extra_run._element.getparent().remove(extra_run._element)
        else:
            paragraph.add_run(text)

    @staticmethod
    def _clone_after(paragraph: Paragraph, text: str) -> Paragraph:
        """Clona ``paragraph`` justo después de él y le pone ``text``.

        Copiar el elemento ``<w:p>`` completo preserva ``pPr`` (estilo, viñeta,
        nivel de lista, sangría) y el formato de los runs.
        """
        new_p = copy.deepcopy(paragraph._p)
        paragraph._p.addnext(new_p)
        new_paragraph = Paragraph(new_p, paragraph._parent)
        DocxWriter._set_text(new_paragraph, text)
        return new_paragraph
