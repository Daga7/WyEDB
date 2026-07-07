"""Puerto del procesador de Word.

Abstrae la lectura/escritura del documento Word para que el caso de uso no dependa
de python-docx. La implementación concreta vive en infraestructura.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ods_reporter.domain.entities.activity import Activity
from ods_reporter.domain.value_objects.content_item import ContentItem


@dataclass(frozen=True, slots=True)
class ActivityInsertResult:
    """Resultado de insertar (o planear) una actividad en el Word."""

    ordinal: int
    matched: bool
    items_written: int
    entregables_matched: int
    entregables_unmatched: int
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class WordActivityOverview:
    """Vista resumida de una actividad del Word (para la vista previa)."""

    ordinal: int
    label: str
    entregable_count: int


class WordProcessorPort(Protocol):
    """Contrato para abrir, rellenar y guardar un documento Word de ODS."""

    def open(self, path: Path) -> None:
        """Carga el documento Word desde ``path``."""
        ...

    def get_activity_ordinals(self) -> list[int]:
        """Devuelve los numerales de las actividades presentes en el documento."""
        ...

    def get_ods_number(self) -> str:
        """Número de ODS detectado en el documento (dígitos), o ``''``."""
        ...

    def get_activities_overview(self) -> list[WordActivityOverview]:
        """Devuelve numeral, título y cantidad de entregables de cada actividad."""
        ...

    def plan_activity_content(self, activity: Activity) -> ActivityInsertResult:
        """Calcula qué ocurriría al insertar ``activity``, sin escribir nada."""
        ...

    def insert_activity_content(
        self, activity: Activity, target_ordinal: int | None = None
    ) -> ActivityInsertResult:
        """Inserta el contenido de ``activity`` (emparejando por numeral y
        alineando entregables por texto). Con ``target_ordinal`` se fuerza el
        destino (reasignación manual). Devuelve el detalle de lo ocurrido.
        """
        ...

    def has_other_activities_section(self) -> bool:
        """``True`` si el documento tiene la sección de observaciones/adicionales."""
        ...

    def insert_other_activities(self, items: tuple[ContentItem, ...]) -> int:
        """Inserta ``items`` como viñetas en la sección de observaciones.

        Devuelve la cantidad insertada (0 si el documento no tiene la sección).
        """
        ...

    def fill_empty_with_default(self, default_text: str) -> int:
        """Rellena con ``default_text`` todos los slots que quedaron vacíos.

        Devuelve la cantidad de slots rellenados. Se llama una sola vez, al final,
        tras procesar a todos los profesionales.
        """
        ...

    def save(self, path: Path) -> None:
        """Guarda el documento en ``path``."""
        ...
