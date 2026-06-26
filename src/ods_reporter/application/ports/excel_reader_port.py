"""Puerto de lectura de Excel.

Define el **contrato** (qué debe ofrecer un lector de Excel) y los objetos de
transferencia (DTO) que entrega. La implementación concreta vive en la capa de
infraestructura (openpyxl), de modo que la lógica de aplicación no dependa de
ninguna librería en particular (inversión de dependencias).

El lector hace una extracción **fiel y "tonta"** de los datos: no filtra ni
interpreta el contenido. La aplicación de reglas de negocio (qué es "vacío",
cómo se parten los ítems) corresponde al normalizador (Fase 5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ods_reporter.domain.entities.ods_metadata import ODSMetadata


@dataclass(frozen=True, slots=True)
class RawEntregable:
    """Un entregable tal como se extrae de una sub-fila del Excel, sin interpretar.

    Attributes
    ----------
    entregable_text:
        Texto crudo de la columna ENTREGABLES (clave para alinear con el Word).
    raw_content:
        Texto crudo de la celda F de esa sub-fila (puede ser multilínea e incluir
        el marcador "no se requirió").
    """

    entregable_text: str
    raw_content: str


@dataclass(frozen=True, slots=True)
class RawActivity:
    """Actividad tal como se extrae del Excel, sin interpretar.

    Attributes
    ----------
    ordinal:
        Número de ID de la columna A.
    label:
        Texto crudo de la columna ACTIVIDADES (puede traer ``\\xa0`` y numeral).
    entregables:
        Entregables de la actividad, uno por cada sub-fila (en orden).
    """

    ordinal: int
    label: str
    entregables: tuple[RawEntregable, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RawReport:
    """Reporte crudo de un Excel para un mes: metadatos + actividades."""

    metadata: ODSMetadata
    activities: tuple[RawActivity, ...] = field(default_factory=tuple)

    @property
    def professional_name(self) -> str:
        return self.metadata.responsible_professional

    @property
    def source_file(self) -> str:
        return self.metadata.source_file


class ExcelReaderPort(Protocol):
    """Contrato de un lector de Excel de reportes ODS."""

    def read_month(self, file_path: Path, month: str) -> RawReport:
        """Lee la hoja del ``month`` indicado y devuelve su reporte crudo.

        Raises
        ------
        InvalidInputError
            Si el archivo no existe o no tiene una extensión válida.
        ExcelReadError
            Si el archivo no se puede abrir, falta la hoja del mes o no se
            reconoce la estructura de la tabla de actividades.
        """
        ...
