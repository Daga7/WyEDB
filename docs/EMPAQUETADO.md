# Empaquetado a ejecutable

ODS Reporter se empaqueta con **PyInstaller** en un **único ejecutable** sin consola.

> ⚠️ **Importante:** PyInstaller genera el ejecutable para el **sistema operativo donde
> se ejecuta**. Para obtener un **`.exe` de Windows hay que compilar EN Windows**
> (no se puede crear un `.exe` desde Linux).

---

## Generar el ejecutable

Con el entorno virtual y las dependencias de desarrollo instaladas:

```bash
pyinstaller ods_reporter.spec
```

El resultado queda en `dist/`:
- En **Windows**: `dist/ODS Reporter.exe`
- En **Linux**: `dist/ODS Reporter`

---

## Generar el `.exe` para Windows

Como estás desarrollando en Linux, hay tres caminos:

### Opción A — Compilar en una máquina/VM Windows (recomendado)
1. Copia el proyecto a un Windows con **Python 3.11+**.
2. Crea el entorno e instala dependencias:
   ```bat
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements-dev.txt
   ```
3. Genera el ejecutable:
   ```bat
   .venv\Scripts\pyinstaller ods_reporter.spec
   ```
4. Entrega `dist\ODS Reporter.exe`.

> En Windows **no** hace falta instalar `tk` aparte: viene incluido con Python.

### Opción B — GitHub Actions (CI en Windows) ✅ IMPLEMENTADO
El workflow [`.github/workflows/build-windows.yml`](../.github/workflows/build-windows.yml)
construye el `.exe` en un runner `windows-latest` y lo publica como artefacto.

**Para usarlo:**
1. Inicializa git y sube el proyecto a GitHub:
   ```bash
   git init && git add . && git commit -m "ODS Reporter"
   git remote add origin <tu-repo-en-github>
   git push -u origin main
   ```
2. En GitHub, pestaña **Actions** → ejecuta *"Construir ejecutable de Windows"*
   (botón **Run workflow**), o crea un tag `v1.0.0` para que lo adjunte a una Release.
3. Descarga el `.exe` desde los **Artifacts** del workflow.

> Nota: los archivos de prueba reales (`.xlsx`/`.docx`) están ignorados por git, por lo
> que en CI las pruebas que los necesitan se omiten automáticamente; el resto se ejecuta.

### Opción C — Wine + PyInstaller
Posible pero frágil (hay que instalar un Python de Windows dentro de Wine). No se
recomienda para entregables de producción.

---

## Reputación y antivirus (falsos positivos)

Los ejecutables de PyInstaller sin firma suelen disparar avisos de SmartScreen,
Chrome o el antivirus ("archivo no seguro" / "poco frecuente"). Mitigaciones
aplicadas y pendientes:

- ✅ **UPX desactivado** en el spec (`upx=False`): la compresión UPX es el
  disparador más común de falsos positivos.
- ✅ **Metadatos de versión** (`packaging/version_info.txt`): empresa
  (S.G.I. S.A.S.), producto y versión visibles en Propiedades → Detalles.
- ⬜ **Icono** (`assets/icon.ico`): el spec lo toma automáticamente si existe.
  Generarlo desde el logo oficial (PNG → ICO multi-resolución 16/32/48/256).
- ⬜ **Distribuir en `.zip`** (Gmail/Drive bloquean `.exe` directos) y publicar
  por **GitHub Releases** para acumular reputación de descarga.
- ⬜ **Firma de código** (solución definitiva): certificado a nombre de
  S.G.I. S.A.S. — Azure Trusted Signing (mensual, reputación inmediata) o
  certificado OV/EV clásico. Reportar además el falso positivo a Microsoft:
  https://www.microsoft.com/en-us/wdsi/filesubmission

## Notas
- El ejecutable incluye Python, las dependencias y los temas de CustomTkinter; el
  usuario final **no instala nada**.
- El primer arranque del onefile puede tardar unos segundos (se descomprime en una
  carpeta temporal).
- El archivo de log se escribe en la carpeta de datos del usuario
  (`%LOCALAPPDATA%\ODS Reporter\logs` en Windows), no junto al ejecutable.
