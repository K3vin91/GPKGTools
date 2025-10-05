# -*- coding: utf-8 -*-
from pathlib import Path
from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsMessageLog,
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject
)

def obtener_nombre_unico(base, existentes):
    nombre = base
    i = 1
    while nombre in existentes:
        nombre = f"{base}_{i}"
        i += 1
    existentes.add(nombre)
    return nombre

def procesar_gpkg(ruta, salida, capas_existentes, resumen, capas_sin_crs, epsg_destino=None, log_cb=None, cancel_cb=None):
    """Procesa todas las capas de un GPKG usando PyQGIS con soporte de log y cancelación."""
    try:
        uri = str(ruta)
        capa_base = QgsVectorLayer(uri, ruta.stem, "ogr")
        for sub in capa_base.dataProvider().subLayers():
            if cancel_cb and cancel_cb():
                if log_cb:
                    log_cb("⏹ Cancelación detectada, deteniendo fusión...")
                return

            nombre_capa = sub.split('!!::!!')[1]
            capa = QgsVectorLayer(f"{uri}|layername={nombre_capa}", nombre_capa, "ogr")
            if not capa.isValid() or capa.featureCount() == 0:
                msg = f"⚠️ {ruta.name} → {nombre_capa}: vacía, ignorada"
                resumen.append(msg)
                if log_cb:
                    log_cb(msg)
                QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Warning)
                continue

            # Reproyección si se indicó EPSG
            if epsg_destino and capa.crs().isValid():
                crs_destino = QgsCoordinateReferenceSystem(epsg_destino)
                transform = QgsCoordinateTransform(capa.crs(), crs_destino, QgsProject.instance())
                capa = capa.clone()
                capa.setCrs(crs_destino)

            nombre_capa_salida = obtener_nombre_unico(f"{ruta.stem}_{nombre_capa}", capas_existentes)

            error = QgsVectorFileWriter.writeAsVectorFormat(
                capa,
                str(salida),
                "utf-8",
                layerName=nombre_capa_salida,
                driverName="GPKG",
                actionOnExistingFile=QgsVectorFileWriter.AppendToLayer
            )

            if error == QgsVectorFileWriter.NoError:
                msg = f"✅ {ruta.name} → {nombre_capa}: exportada como {nombre_capa_salida}"
            else:
                msg = f"❌ {ruta.name} → {nombre_capa}: error al exportar"
            resumen.append(msg)
            if log_cb:
                log_cb(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info if error == QgsVectorFileWriter.NoError else Qgis.Critical)

    except Exception as e:
        msg = f"❌ {ruta.name}: error durante la fusión → {e}"
        resumen.append(msg)
        if log_cb:
            log_cb(msg)
        QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)

def fusionar_vectores(carpeta, salida, epsg_destino=None, log_cb=None, cancel_cb=None):
    """Fusiona todos los GPKG de una carpeta en un único GPKG usando PyQGIS con log y cancelación."""
    carpeta = Path(carpeta)
    salida = Path(salida)

    # Asegurar que sea un archivo .gpkg
    if salida.is_dir() or salida.suffix.lower() != ".gpkg":
        salida.mkdir(parents=True, exist_ok=True)
        salida = salida / "fusion.gpkg"

    if salida.exists():
        salida.unlink()

    capas_existentes = set()
    resumen = []
    capas_sin_crs = []
    total_archivos = 0
    procesados = 0
    fallidos = 0

    for file in carpeta.rglob("*.gpkg"):
        if cancel_cb and cancel_cb():
            if log_cb:
                log_cb("⏹ Cancelación detectada, deteniendo fusión...")
            break

        if file.is_file():
            total_archivos += 1
            try:
                procesar_gpkg(file, salida, capas_existentes, resumen, capas_sin_crs, epsg_destino, log_cb, cancel_cb)
                procesados += 1
            except Exception as e:
                msg = f"❌ {file.name}: error durante la fusión → {e}"
                resumen.append(msg)
                if log_cb:
                    log_cb(msg)
                QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)
                fallidos += 1

    # Guardar resumen
    resumen_path = salida.with_name(salida.stem + "_resumen.txt")
    with open(resumen_path, "w", encoding="utf-8") as f:
        f.write("📘 RESUMEN DE FUSIÓN DE GPKG\n\n")
        f.write(f"📂 Carpeta procesada: {carpeta}\n")
        f.write(f"💾 Archivo de salida: {salida}\n\n")
        f.write(f"Total de archivos GPKG procesados: {total_archivos}\n")
        f.write(f"Archivos fusionados correctamente: {procesados}\n")
        f.write(f"Archivos con errores: {fallidos}\n\n")
        if capas_sin_crs:
            f.write("⚠️ Capas sin CRS (requieren revisión manual):\n")
            f.write("\n".join(capas_sin_crs) + "\n")
        f.write("\n--- Detalle de ejecución ---\n")
        f.write("\n".join(resumen))

    if log_cb:
        log_cb(f"✅ Fusión completada en: {salida}")
        log_cb(f"📝 Resumen guardado en: {resumen_path}")

    QgsMessageLog.logMessage(f"✅ Fusión completada en: {salida}", "GPKG Tools", Qgis.Info)
    QgsMessageLog.logMessage(f"📝 Resumen guardado en: {resumen_path}", "GPKG Tools", Qgis.Info)

    return salida, resumen_path
