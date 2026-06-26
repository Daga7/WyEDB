"""Jerarquía de excepciones del dominio.

Todas heredan de ``ODSReporterError`` para que cualquier capa pueda capturar
los errores propios de la aplicación de forma uniforme y diferenciarlos de los
errores inesperados del sistema.
"""

from __future__ import annotations


class ODSReporterError(Exception):
    """Error base de la aplicación."""


class InvalidInputError(ODSReporterError):
    """Una entrada del usuario no es válida (archivo, carpeta o mes incorrectos)."""


class TemplateNotFoundError(ODSReporterError):
    """No se encontró la plantilla Word indicada."""


class ExcelReadError(ODSReporterError):
    """No se pudo leer correctamente un archivo Excel."""


class WordProcessError(ODSReporterError):
    """Ocurrió un error al procesar o guardar el documento Word."""


class ActivityNotFoundError(ODSReporterError):
    """Una actividad presente en el Excel no se encontró en el documento Word."""
