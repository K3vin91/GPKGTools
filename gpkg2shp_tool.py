# -*- coding: utf-8 -*-
from pathlib import Path
from qgis.core import (
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsVectorFileWriter,
    QgsProject,
    QgsCoordinateTransform,
    QgsFeature,
    QgsWkbTypes
)
from osgeo import ogr

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
            ds = ogr.Open(str(ruta_gpkg))
            if ds is None:
                raise Exception("No se pudo abrir el GPKG con OGR.")

            capas_nombres = [ds.GetLayerByIndex(i).GetName() for i in range(ds.GetLayerCount())]
            if log_callback:
                log_callback(f"📦 Procesando GPKG: {ruta_gpkg.name} → {len(capas_nombres)} capas encontradas")

        except Exception as e:
            msg = f"❌ {ruta_gpkg.name}: fallo al listar capas → {e}"
            if log_callback:
                log_callback(msg)
            resumen.append(msg)
            continue

        contador_sin_nombre = 1
        for nombre_original in capas_nombres:
            nombre_export = None
            try:
                if not nombre_original:
                    msg = f"⚠️ {ruta_gpkg.stem}: capa sin nombre #{contador_sin_nombre} → omitida."
                    contador_sin_nombre += 1
                    resumen.append(msg)
                    if log_callback:
                        log_callback(msg)
                    continue

                nombre_export = nombre_original
                mensaje_extra = ""

                # Construir URI seguro para cargar capa
                uri = f"{ruta_gpkg}|layername={nombre_original}"
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
                    if log_callback:
                        log_callback(msg)

                # Crear capa en memoria con geometría correcta
                geom_type = QgsWkbTypes.displayString(layer.wkbType())
                mem_layer = QgsVectorLayer(f"{geom_type}?crs={crs_destino.authid()}", nombre_export, "memory")
                mem_layer_data = mem_layer.dataProvider()
                mem_layer_data.addAttributes(layer.fields())
                mem_layer.updateFields()

                # Transformar geometrías si es necesario
                xform = None
                if layer.crs() != crs_destino:
                    xform = QgsCoordinateTransform(layer.crs(), crs_destino, transform_context)
                    mensaje_extra += f" (Reproyectado a EPSG:{crs_destino.postgisSrid()})"

                for feat in layer.getFeatures():
                    geom = feat.geometry()
                    if geom and xform:
                        geom.transform(xform)
                    new_feat = QgsFeature()
                    new_feat.setGeometry(geom)
                    new_feat.setAttributes(feat.attributes())
                    mem_layer_data.addFeature(new_feat)

                export_layer = mem_layer

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
                options.fileEncoding = "UTF-8"

                result, error_message = QgsVectorFileWriter.writeAsVectorFormatV2(
                    export_layer,
                    str(ruta_salida),
                    transform_context,
                    options
                )
                if result != QgsVectorFileWriter.NoError:
                    raise Exception(error_message)

                resumen.append(f"{ruta_gpkg.stem}:{nombre_export} → convertido{mensaje_extra}")
                if log_callback:
                    log_callback(f"✅ {ruta_gpkg.stem}:{nombre_export} → convertido{mensaje_extra}")

            except Exception as e:
                resumen.append(f"{ruta_gpkg.stem}:{nombre_export} → fallido → {e}")
                if log_callback:
                    log_callback(f"❌ {ruta_gpkg.stem}:{nombre_export} → fallido → {e}")

    # Guardar resumen
    ruta_resumen = carpeta_salida / "resumen_conversion.txt"
    with open(ruta_resumen, "w", encoding="utf-8") as f:
        f.write("\n".join(resumen))

    return ruta_resumen
