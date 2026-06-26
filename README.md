# ODS Reporter

**Automatiza la generación de informes ODS**: traslada la información diligenciada en
archivos **Excel** (uno por profesional, por mes) a los documentos **Word** existentes de
cada ODS, **conservando el formato original al 100%**.

Reduce un proceso manual de varias horas a unos pocos minutos.

---

## ⬇️ Descargar la aplicación (Windows)

> El ejecutable se construye automáticamente en GitHub Actions.

1. Ve a la pestaña **[Actions](../../actions)** del repositorio.
2. Abre la ejecución más reciente de **«Construir ejecutable de Windows»**.
3. En **Artifacts**, descarga **`ODS-Reporter-Windows`** (contiene `ODS Reporter.exe`).
4. Descomprime y ejecuta **`ODS Reporter.exe`** — no requiere instalar nada.

> Si hay una **[Release](../../releases)** publicada, puedes descargar el `.exe`
> directamente desde ahí.

---

## ¿Qué hace?

1. Tomas la **plantilla Word** de una ODS (con sus actividades ya escritas).
2. Cargas **uno o varios Excel** (uno por profesional) y eliges el **mes**.
3. La app localiza cada actividad en el Word (por numeral + texto) e inserta el contenido
   del Excel debajo de cada actividad/entregable.
4. Las actividades sin información reciben el texto estándar
   *«Durante el periodo se estuvo atento a cualquier solicitud pero no se requirió el servicio»*.
5. Genera un **resumen** (profesionales sin actividades o con menos de 5) y un **reporte**.

El documento original **nunca** se modifica: el resultado se guarda en la carpeta de salida.

### Soporta múltiples plantillas
Reconoce automáticamente distintos formatos de ODS (numeración romana o arábiga, con o sin
columna de entregables) y procesa cualquiera de ellos.

---

## 🖥️ Uso de la interfaz

1. **Plantilla Word (.docx):** la plantilla en blanco de la ODS.
2. **Archivos Excel:** «Agregar archivos» o «Agregar carpeta» (uno por profesional).
3. **Carpeta de salida:** dónde se guarda el documento generado.
4. **Mes:** la pestaña del Excel a procesar.
5. Pulsa **Iniciar**. Sigue el avance en la consola y revisa el **resumen** al final.

---

## 🧑‍💻 Desarrollo

Requisitos: **Python 3.11+**. En Linux (Arch/CachyOS), para la interfaz: `sudo pacman -S tk`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt

# Ejecutar la aplicación
PYTHONPATH=src .venv/bin/python -m ods_reporter.main

# Ejecutar las pruebas
.venv/bin/python -m pytest -q
```

### Construir el ejecutable
```bash
pyinstaller ods_reporter.spec
```
Ver [docs/EMPAQUETADO.md](docs/EMPAQUETADO.md) para generar el `.exe` de Windows.

---

## 🏗️ Arquitectura

Proyecto basado en **Clean Architecture** (4 capas). Detalles en
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
src/ods_reporter/
├── domain/          # Entidades y reglas de negocio puras
├── application/     # Casos de uso, puertos y servicios
├── infrastructure/  # Excel (openpyxl), Word (python-docx), logging, archivos
├── presentation/    # Interfaz gráfica (CustomTkinter, MVVM)
└── shared/          # Utilidades transversales
```

Calidad: **128 pruebas** automatizadas (unitarias e integración con archivos reales).

---

## Licencia

Uso interno. Todos los derechos reservados.
