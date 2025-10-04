# -*- coding: utf-8 -*-
from pathlib import Path
from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsWkbTypes,
    QgsProject
)


def convertir_shapefiles(carpeta_entrada, carpeta_salida, epsg_destino=None,
                         cancel_callback=None, log_callback=None):
    """
    Convierte todos los shapefiles de una carpeta a GPKG usando PyQGIS,
    respetando la estructura de subcarpetas de la carpeta de entrada.
    Cada shapefile genera un GeoPackage independiente.
    """

    carpeta_entrada = Path(carpeta_entrada)
    carpeta_salida = Path(carpeta_salida)

    shapefiles = list(carpeta_entrada.rglob("*.shp"))
    resumen = []

    transform_context = QgsProject.instance().transformContext()

    for ruta in shapefiles:
        if cancel_callback and cancel_callback():
            msg = "⏹ Conversión cancelada por el usuario."
            if log_callback:
                log_callback(msg)
            resumen.append("Cancelado por el usuario.")
            break

        try:
            # Cargar shapefile
            layer = QgsVectorLayer(str(ruta), ruta.stem, "ogr")
            if not layer.isValid():
                raise Exception("No se pudo cargar la capa.")

            mensaje_extra = ""

            # Determinar CRS destino
            if epsg_destino:
                crs_destino = QgsCoordinateReferenceSystem.fromEpsgId(epsg_destino)
            elif layer.crs().isValid():
                crs_destino = layer.crs()
            else:
                crs_destino = QgsCoordinateReferenceSystem.fromEpsgId(4326)

            # Advertencia si CRS original no válido
            if not layer.crs().isValid():
                mensaje_extra = f" (CRS indefinido → EPSG:{crs_destino.postgisSrid()})"
                msg = f"⚠️ {ruta.stem}: CRS indefinido → EPSG:{crs_destino.postgisSrid()}"
                QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Warning)
                if log_callback:
                    log_callback(msg)

            # Reproyectar si EPSG destino es distinto
            if layer.crs() != crs_destino:
                transform = QgsCoordinateTransform(layer.crs(), crs_destino, QgsProject.instance())

                # Detectar tipo de geometría original (Point, LineString, Polygon)
                geom_type = QgsWkbTypes.displayString(layer.wkbType())
                mem_layer_uri = "{}?crs={}".format(geom_type, crs_destino.authid())

                mem_layer = QgsVectorLayer(mem_layer_uri, layer.name(), "memory")
                mem_layer.startEditing()
                mem_layer.dataProvider().addAttributes(layer.fields())
                mem_layer.updateFields()

                for feat in layer.getFeatures():
                    new_feat = QgsFeature()
                    new_feat.setFields(layer.fields())
                    new_feat.setAttributes(feat.attributes())
                    geom = feat.geometry()
                    if geom:
                        geom.transform(transform)
                        new_feat.setGeometry(geom)
                    mem_layer.addFeature(new_feat)

                mem_layer.commitChanges()
                export_layer = mem_layer
                mensaje_extra = f" (Reproyectado a EPSG:{crs_destino.postgisSrid()})"
            else:
                export_layer = layer

            # Construir ruta de salida respetando subcarpetas
            ruta_relativa = ruta.relative_to(carpeta_entrada).parent
            carpeta_salida_completa = carpeta_salida / ruta_relativa
            carpeta_salida_completa.mkdir(parents=True, exist_ok=True)
            ruta_salida = carpeta_salida_completa / (ruta.stem + ".gpkg")

            # Si el GPKG existe, borrarlo antes de crear uno nuevo
            if ruta_salida.exists():
                ruta_salida.unlink()

            # Guardar en GeoPackage
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GPKG"
            options.layerName = ruta.stem

            result, error_message = QgsVectorFileWriter.writeAsVectorFormatV2(
                export_layer,
                str(ruta_salida),
                transform_context,
                options
            )

            if result != QgsVectorFileWriter.NoError:
                raise Exception(error_message)

            resumen.append(f"{ruta.stem}: convertido{mensaje_extra}")
            msg = f"✅ {ruta.stem}: convertido{mensaje_extra}"
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info)
            if log_callback:
                log_callback(msg)

        except Exception as e:
            resumen.append(f"{ruta.stem}: fallido → {e}")
            msg = f"❌ {ruta.stem}: fallido → {e}"
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)
            if log_callback:
                log_callback(msg)

    # Guardar resumen
    ruta_resumen = carpeta_salida / "resumen_conversion.txt"
    with open(ruta_resumen, "w", encoding="utf-8") as f:
        f.write("\n".join(resumen))

    msg = f"📝 Resumen guardado en: {ruta_resumen}"
    QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info)
    if log_callback:
        log_callback(msg)

    return ruta_resumen
