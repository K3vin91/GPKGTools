============================================================
📦 GpkgTools – Plugin para QGIS
============================================================

GpkgTools es un conjunto de herramientas para gestionar, convertir
y fusionar archivos GeoPackage (GPKG) y Shapefiles (SHP) en QGIS
de manera rápida y eficiente. Todas las herramientas procesan los
archivos encontrados en la carpeta seleccionada y sus subcarpetas.

------------------------------------------------------------
🛠 Herramientas incluidas
------------------------------------------------------------

1️⃣ shp2gpkg – Shapefile → GeoPackage
------------------------------------
Convierte uno o varios Shapefiles en un único GeoPackage.
Características principales:
- Examina todas las subcarpetas de la carpeta seleccionada.
- Permite declarar un EPSG de destino para reproyectar todas
  las capas procesadas.
- Genera un log con todas las capas convertidas, incluyendo
  su EPSG original y el EPSG de reproyección si se aplica.

2️⃣ gpkg2shp – GeoPackage → Shapefile
------------------------------------
Extrae todas las capas de uno o varios GeoPackages y las
exporta como Shapefiles.
Características principales:
- Examina todas las subcarpetas de la carpeta seleccionada.
- Permite declarar un EPSG de destino para reproyectar todas
  las capas exportadas.
- Mantiene la estructura de carpetas para organizar los SHP.
- Genera un log con todas las capas exportadas, incluyendo
  su EPSG original y el EPSG de reproyección si se aplica.

3️⃣ gpkg2fusion – Fusionar GeoPackages
-------------------------------------
Fusiona todos los GeoPackages de una carpeta (y sus subcarpetas)
en un único GeoPackage de salida.
Características principales:
- Conserva el EPSG original de cada capa (no se reproyecta).
- Genera un log y un resumen detallado que indica:
    • Capas fusionadas correctamente
    • Capas vacías ignoradas
    • Archivos con errores
    • EPSG de cada capa
- Compatible con GeoPackages grandes y múltiples capas.

------------------------------------------------------------
⚙️ Requisitos
------------------------------------------------------------
- QGIS 3.x (probado hasta la versión 3.34)
- Python 3
- Librerías incluidas en QGIS: PyQt5, osgeo/OGR
- Sistema operativo: Windows, Linux o macOS con QGIS instalado

------------------------------------------------------------
📥 Instalación
------------------------------------------------------------
1. Copia la carpeta completa `gpkg_tools` en tu directorio de plugins:

   Windows: %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins
   Linux:   ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins
   macOS:   ~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins

2. Abre QGIS y activa el plugin desde:
   Complementos → Administrar e instalar complementos

3. Reinicia QGIS si es necesario.

------------------------------------------------------------
🖥 Uso
------------------------------------------------------------
- Selecciona la carpeta de entrada.
- Selecciona el archivo o carpeta de salida.
- (Opcional) Indica un EPSG de destino en shp2gpkg o gpkg2shp.
- Ejecuta la herramienta y revisa el registro de ejecución.
- Cada herramienta genera un archivo `_resumen.txt` en la
  misma ubicación del archivo de salida.

------------------------------------------------------------
⚠️ Advertencias
------------------------------------------------------------
- Si el archivo de salida ya existe, será sobrescrito.
- Las capas vacías se ignoran y quedan registradas en el resumen.
- La cancelación detiene la tarea antes de iniciar la fusión de
  un nuevo archivo, pero no interrumpe capas ya copiadas.
- EPSG opcional:
    • En shp2gpkg y gpkg2shp permite reproyectar todas las capas.
    • En gpkg2fusion no se aplica; las capas conservan su CRS original.

------------------------------------------------------------
📄 Resumen de ejecución
------------------------------------------------------------
- Archivos procesados y fusionados
- Errores
- CRS de cada capa (para gpkg2fusion, se registra el EPSG original)

------------------------------------------------------------
🛠 Desarrollo y Contribución
------------------------------------------------------------
- Los scripts se encuentran en la carpeta `gpkg_tools`.
- Para editar interfaces gráficas, abre los archivos `.ui` en
  Qt Designer.
- Reporta errores o sugerencias en tu repositorio o vía correo.

------------------------------------------------------------
📜 Licencia
------------------------------------------------------------
(C) 2025 Kevin Irias  
Uso libre para fines personales y educativos. Para uso comercial,
contactar al autor.

