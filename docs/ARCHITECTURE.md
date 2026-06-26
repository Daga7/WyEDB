# Arquitectura — ODS Reporter

Documento de referencia del diseño. Se mantiene actualizado a medida que avanzan las fases.

## Objetivo

Automatizar el traslado de información desde archivos **Excel** (uno por profesional, por
mes) hacia los documentos **Word** existentes de cada ODS, **conservando el formato al 100%**.

## Estilo: Clean Architecture (4 capas)

Las dependencias apuntan hacia el núcleo. La GUI y la infraestructura dependen del dominio,
nunca al revés. Esto permite probar la lógica de negocio sin abrir la interfaz.

```
PRESENTATION  (CustomTkinter, MVVM)        → la cara visible
APPLICATION   (casos de uso, orquestación) → el "qué hacer"
DOMAIN        (entidades, reglas puras)    → el corazón
INFRASTRUCTURE(Excel, Word, archivos, log) → el "cómo"
```

## Estructura

```
src/ods_reporter/
├── domain/          # Entidades y reglas de negocio puras (sin dependencias externas)
├── application/     # Puertos (interfaces), servicios y casos de uso
├── infrastructure/  # openpyxl (Excel), python-docx (Word), logging, archivos
├── presentation/    # Interfaz gráfica (CustomTkinter) con patrón MVVM
└── shared/          # Result[T], constantes, contenedor de dependencias
```

## Decisiones técnicas

| Tema | Decisión | Motivo |
|---|---|---|
| Lenguaje | Python 3.11+ | Ecosistema Excel/Word |
| Excel | openpyxl | Acceso preciso a celdas y celdas combinadas |
| Word | python-docx | Inserción a nivel XML preservando formato |
| Emparejado | rapidfuzz | Coincidencia robusta numeral + texto |
| GUI | CustomTkinter | Moderna, ligera, fácil de empaquetar |
| Errores | `Result[T]` | Un fallo no detiene todo el proceso |

## Flujo de datos

1. Usuario elige: plantilla Word + varios Excel + carpeta de salida + mes.
2. El `ProcessODSUseCase` copia la plantilla a la salida (el original no se toca).
3. Por cada Excel: se lee la pestaña del mes → profesional + actividades con contenido.
4. El contenido (columna F) se normaliza a ítems con guion (se quita numeración).
5. Cada actividad se localiza en el Word (numeral + texto) y se inserta debajo del guion.
6. Las actividades sin información reciben el texto estándar.
7. Se audita a los profesionales (sin actividades / menos de 5) y se genera log + resumen.

## Reglas de negocio clave

- Emparejamiento por **numeral + texto** (el numeral desempata textos repetidos).
- La columna F puede venir con saltos de línea, numeración o guiones → se normaliza.
- `"No se requirió esta actividad..."` cuenta como **sin contenido**.
- El contenido de varios profesionales se concatena como ítems, sin nombrar al profesional.
- Cada mes parte de la **plantilla original limpia**.

## Estado por fases

- [x] Fase 1 — Análisis y arquitectura
- [x] Fase 2 — Configuración del proyecto
- [x] Fase 3 — Dominio
- [x] Fase 4 — Lectura de Excel
- [x] Fase 5 — Normalización de contenido
- [x] Fase 6 — Emparejamiento de actividades
- [x] Fase 7 — Procesamiento de Word
- [x] Fase 8 — Orquestación
- [x] Fase 9 — Reportes y auditoría
- [x] Fase 10 — Interfaz gráfica
- [~] Fase 11 — Integración y robustez (validado con 7 Excel reales; lector Word genérico para nuevas plantillas)
- [x] Fase 12 — Empaquetado (spec PyInstaller; binario Linux verificado; .exe requiere build en Windows)
- [ ] Fase 13 — Optimización
