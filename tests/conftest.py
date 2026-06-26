"""Configuración y fixtures compartidos de pytest."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXCEL_FIXTURE = FIXTURES_DIR / "ODS11_2026_Mayo.xlsx"
WORD_FIXTURE = FIXTURES_DIR / "ODS11_Word.docx"
WORD_BLANK_FIXTURE = FIXTURES_DIR / "ODS11_Word_blank.docx"


@pytest.fixture
def excel_fixture() -> Path:
    """Ruta al Excel real de ejemplo (ODS 11, mayo 2026)."""
    if not EXCEL_FIXTURE.exists():
        pytest.skip(f"Falta el fixture de Excel: {EXCEL_FIXTURE}")
    return EXCEL_FIXTURE


@pytest.fixture
def word_fixture() -> Path:
    """Ruta al Word real de ejemplo (ODS 11, abril, ya diligenciado)."""
    if not WORD_FIXTURE.exists():
        pytest.skip(f"Falta el fixture de Word: {WORD_FIXTURE}")
    return WORD_FIXTURE


@pytest.fixture
def word_blank_fixture() -> Path:
    """Ruta a la plantilla Word EN BLANCO (ODS 11), el insumo real de cada mes."""
    if not WORD_BLANK_FIXTURE.exists():
        pytest.skip(f"Falta la plantilla en blanco: {WORD_BLANK_FIXTURE}")
    return WORD_BLANK_FIXTURE
