"""Plan de inserción: qué se escribiría en el Word, sin escribirlo todavía.

Es el insumo de la **vista previa**: la interfaz muestra el plan, el usuario
decide qué hacer con el contenido sin ubicación (elegir un numeral de destino u
omitirlo) y la fase de aplicación ejecuta esas decisiones sobre el documento.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ods_reporter.application.ports.word_processor_port import WordActivityOverview
from ods_reporter.domain.entities.professional import Professional

# Decisiones del usuario sobre el contenido sin ubicación. La clave identifica la
# actividad (índice del profesional en el plan, numeral del Excel); el valor es
# el numeral del Word elegido como destino, o ``None`` para omitirla.
PlanOverrides = dict[tuple[int, int], int | None]


@dataclass(frozen=True, slots=True)
class PlannedActivity:
    """Una actividad con contenido del Excel y lo que ocurrirá al generar."""

    professional_index: int
    professional_name: str
    source_file: str
    ordinal: int
    label: str
    items_count: int
    matched: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def key(self) -> tuple[int, int]:
        """Clave que identifica esta actividad dentro de ``PlanOverrides``."""
        return (self.professional_index, self.ordinal)


@dataclass(frozen=True, slots=True)
class ODSPlan:
    """Resultado de la fase de análisis, listo para previsualizar y aplicar."""

    month: str
    word_activities: tuple[WordActivityOverview, ...]
    planned: tuple[PlannedActivity, ...]
    professionals: tuple[Professional, ...]
    read_errors: tuple[str, ...] = field(default_factory=tuple)
    cancelled: bool = False
    # Actividades adicionales ("otras actividades solicitadas") detectadas en
    # los Excel, y si el Word tiene la sección de observaciones donde insertarlas.
    other_activities_count: int = 0
    word_has_other_section: bool = False
    general_warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def unmatched(self) -> tuple[PlannedActivity, ...]:
        """Actividades del Excel que no encontraron su numeral en el Word."""
        return tuple(p for p in self.planned if not p.matched)

    @property
    def warnings(self) -> tuple[str, ...]:
        planned_warnings = tuple(w for p in self.planned for w in p.warnings)
        return planned_warnings + self.general_warnings

    def items_for_word_ordinal(self, ordinal: int) -> int:
        """Viñetas que se insertarán en la actividad ``ordinal`` del Word."""
        return sum(p.items_count for p in self.planned if p.matched and p.ordinal == ordinal)
