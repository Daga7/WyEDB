"""Entidad ``ODSMetadata``: datos de cabecera leídos del Excel.

Información contextual de la ODS y del periodo. Los campos son opcionales porque
no todos los Excel los traen completos; el mapeo exacto de celdas se define en la
Fase 4 (lectura de Excel).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ODSMetadata:
    """Metadatos de cabecera de un Excel de ODS."""

    ods_number: str = ""
    contract_number: str = ""
    client: str = ""
    responsible_professional: str = ""
    reported_period: str = ""
    source_file: str = ""
