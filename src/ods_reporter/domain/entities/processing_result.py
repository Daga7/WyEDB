"""Entidades del resultado del procesamiento.

Modelan el desenlace de una ejecución completa: contadores agregados, errores,
advertencias, auditoría de profesionales y tiempos. La presentación (panel/resumen)
y el generador de reportes consumen esto.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ProfessionalAudit:
    """Resultado de la auditoría de profesionales (Fase 9).

    Attributes
    ----------
    without_activities:
        Nombres de profesionales que no reportaron ninguna actividad.
    below_threshold:
        Pares (nombre, cantidad) de profesionales con menos del mínimo requerido.
    """

    without_activities: tuple[str, ...] = field(default_factory=tuple)
    below_threshold: tuple[tuple[str, int], ...] = field(default_factory=tuple)


@dataclass(slots=True)
class ProcessingResult:
    """Resumen agregado del resultado de una ejecución completa.

    Es mutable a propósito: el caso de uso lo va alimentando durante el proceso.
    """

    professionals_processed: int = 0
    activities_with_content: int = 0
    activities_not_found: int = 0
    items_written: int = 0
    other_activities_written: int = 0
    default_slots_filled: int = 0
    entregables_unmatched: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    audit: ProfessionalAudit | None = None
    elapsed_seconds: float = 0.0
    output_path: str = ""
    cancelled: bool = False
    summary: str = ""

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
