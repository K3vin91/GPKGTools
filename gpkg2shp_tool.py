# -*- coding: utf-8 -*-
from pathlib import Path
from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsProject
)

def convertir_gpkg_a_shp(carpeta_entrada, carpeta_salida, epsg_destino=None,
                         cancel_callback=None, log_callback=None):
    """
    Convierte todas las capas de GeoPackages a shapefiles usando PyQGIS.
    Cada capa se exporta como un SHP independiente.
    Se respeta la estructura de subcarpetas y se sobrescriben archivos existentes.
    Capas sin nombre se omiten y se reportan en log/resumen con contador.
    """
    carpeta_entrada = Path(carpeta_entrada)
    carpeta_salida = Path(carpeta_salida)
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    geopackages = list(carpeta_entrada.rglob("*.gpkg"))
    resumen = []

    transform_context = QgsProject.instance().transformContext()

    for ruta_gpkg in geopackages:
        if cancel_callback and cancel_callback():
            msg = "⏹ Conversión cancelada por el usuario."
            if log_callback:
                log_callback(msg)
            resumen.append("Cancelado por el usuario.")
            break

        try:
            temp_layer = QgsVectorLayer(str(ruta_gpkg), "temp", "ogr")
            if not temp_layer.isValid():
                raise Exception("No se pudo cargar el GPKG para obtener capas.")
            capas_raw = temp_layer.dataProvider().subLayers()
            capas_nombres = [c.split(":")[1].strip() for c in capas_raw]
            if log_callback:
                log_callback(f"📦 Procesando GPKG: {ruta_gpkg.name} → {len(capas_nombres)} capas encontradas")
        except Exception as e:
            msg = f"❌ {ruta_gpkg.name}: fallo al listar capas → {e}"
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)
            if log_callback:
                log_callback(msg)
            resumen.append(msg)
            continue

        contador_sin_nombre = 1
        for nombre_original in capas_nombres:
            nombre_export = None
            try:
                # Si la capa no tiene nombre → omitir con contador
                if not nombre_original:
                    msg = f"⚠️ {ruta_gpkg.stem}: capa sin nombre #{contador_sin_nombre} → omitida."
                    contador_sin_nombre += 1
                    resumen.append(msg)
                    QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Warning)
                    if log_callback:
                        log_callback(msg)
                    continue

                nombre_export = nombre_original
                mensaje_extra = ""

                # Construir URI seguro
                uri = f"{ruta_gpkg}|layername=\"{nombre_original}\""
                layer = QgsVectorLayer(uri, nombre_export, "ogr")
                if not layer.isValid():
                    raise Exception(f"No se pudo cargar la capa '{nombre_original}' desde {ruta_gpkg.name}")

                # Determinar CRS destino
                if epsg_destino:
                    crs_destino = QgsCoordinateReferenceSystem.fromEpsgId(epsg_destino)
                elif layer.crs().isValid():
                    crs_destino = layer.crs()
                else:
                    crs_destino = QgsCoordinateReferenceSystem.fromEpsgId(4326)

                if not layer.crs().isValid():
                    mensaje_extra += f" (CRS indefinido → EPSG:{crs_destino.postgisSrid()})"
                    msg = f"⚠️ {ruta_gpkg.stem}:{nombre_export} → CRS indefinido, asignado EPSG:{crs_destino.postgisSrid()}"
                    QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Warning)
                    if log_callback:
                        log_callback(msg)

                # Reproyectar si es necesario
                if layer.crs() != crs_destino:
                    mem_layer = QgsVectorLayer(
                        "{}?crs={}".format(layer.dataProvider().dataSourceUri(), crs_destino.postgisSrid()),
                        layer.name(),
                        "memory"
                    )
                    mem_layer.startEditing()
                    for f in layer.getFeatures():
                        mem_layer.addFeature(f)
                    mem_layer.commitChanges()
                    export_layer = mem_layer
                    if "(Reproyectado" not in mensaje_extra:
                        mensaje_extra += f" (Reproyectado a EPSG:{crs_destino.postgisSrid()})"
                else:
                    export_layer = layer

                # Ruta de salida
                ruta_relativa = ruta_gpkg.relative_to(carpeta_entrada).parent
                ruta_salida = carpeta_salida / ruta_relativa / f"{nombre_export}.shp"
                ruta_salida.parent.mkdir(parents=True, exist_ok=True)

                # Eliminar SHP existente
                for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                    f = ruta_salida.with_suffix(ext)
                    if f.exists():
                        f.unlink()

                # Guardar SHP
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "ESRI Shapefile"

                result, error_message = QgsVectorFileWriter.writeAsVectorFormatV2(
                    export_layer,
                    str(ruta_salida),
                    transform_context,
                    options
                )
                if result != QgsVectorFileWriter.NoError:
                    raise Exception(error_message)

                resumen.append(f"{ruta_gpkg.stem}:{nombre_export} → convertido{mensaje_extra}")
                msg = f"✅ {ruta_gpkg.stem}:{nombre_export} → convertido{mensaje_extra}"
                QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info)
                if log_callback:
                    log_callback(msg)

            except Exception as e:
                resumen.append(f"{ruta_gpkg.stem}:{nombre_export} → fallido → {e}")
                msg = f"❌ {ruta_gpkg.stem}:{nombre_export} → fallido → {e}"
                QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)
                if log_callback:
                    log_callback(msg)

    # Guardar resumen
    ruta_resumen = carpeta_salida / "resumen_conversion.txt"
    with open(ruta_resumen, "w", encoding="utf-8") as f:
        f.write("\n".join(resumen))

    return ruta_resumen
