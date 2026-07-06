"""Formateador del resumen del procesamiento.

Genera un texto legible a partir de un ``ProcessingResult``. Es puro (sin E/S),
de modo que lo reutilizan tanto el panel de la interfaz como el archivo de reporte.
"""

from __future__ import annotations

from ods_reporter.domain.entities.processing_result import ProcessingResult
from ods_reporter.shared.constants import APP_NAME, APP_VERSION, MIN_ACTIVITIES_THRESHOLD


class ReportFormatter:
    """Construye el resumen de una ejecución en texto plano."""

    def format(self, result: ProcessingResult, *, month: str = "") -> str:
        lines: list[str] = []
        add = lines.append

        add(f"{APP_NAME} v{APP_VERSION} — Resumen del procesamiento")
        if month:
            add(f"Mes procesado: {month}")
        add("=" * 60)

        if result.cancelled:
            add("⚠  PROCESO CANCELADO POR EL USUARIO")
            add("-" * 60)

        add(f"Profesionales procesados : {result.professionals_processed}")
        add(f"Actividades con contenido: {result.activities_with_content}")
        add(f"Viñetas insertadas       : {result.items_written}")
        add(f"Actividades adicionales  : {result.other_activities_written}")
        add(f"Slots con texto estándar : {result.default_slots_filled}")
        add(f"Actividades no encontradas: {result.activities_not_found}")
        add(f"Entregables sin alinear  : {result.entregables_unmatched}")
        add(f"Tiempo total             : {result.elapsed_seconds:.2f} s")
        if result.output_path:
            add(f"Documento generado       : {result.output_path}")

        self._append_audit(lines, result)
        self._append_messages(lines, "ADVERTENCIAS", result.warnings)
        self._append_messages(lines, "ERRORES", result.errors)

        add("=" * 60)
        if result.has_errors:
            add("Resultado: completado CON ERRORES (revise el detalle).")
        elif result.cancelled:
            add("Resultado: incompleto (cancelado).")
        else:
            add("Resultado: completado correctamente.")

        return "\n".join(lines)

    @staticmethod
    def _append_audit(lines: list[str], result: ProcessingResult) -> None:
        audit = result.audit
        if audit is None:
            return
        lines.append("-" * 60)
        lines.append("AUDITORÍA DE PROFESIONALES (seguimiento)")
        if audit.without_activities:
            lines.append("  Sin actividades reportadas:")
            for name in audit.without_activities:
                lines.append(f"    • {name}")
        if audit.below_threshold:
            lines.append(f"  Con menos de {MIN_ACTIVITIES_THRESHOLD} actividades:")
            for name, count in audit.below_threshold:
                lines.append(f"    • {name} ({count})")
        if not audit.without_activities and not audit.below_threshold:
            lines.append("  Todos los profesionales cumplen el mínimo.")

    @staticmethod
    def _append_messages(lines: list[str], title: str, messages: list[str]) -> None:
        if not messages:
            return
        lines.append("-" * 60)
        lines.append(f"{title} ({len(messages)})")
        if title == "ERRORES":
            lines.append("  (cada línea indica el archivo/profesional para revisarlo a detalle)")
        for message in messages:
            lines.append(f"  • {message}")
