import os
from pathlib import Path
import geopandas as gpd
from pyproj import CRS
import fiona

from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.core import Qgis, QgsMessageLog


def convertir_geopackages(carpeta_entrada, carpeta_salida, epsg_destino=None):
    """
    Convierte todas las capas de GeoPackages a shapefiles.
    """
    geopackages = list(carpeta_entrada.rglob("*.gpkg"))
    total = len(geopackages)
    exitosos, sin_crs = 0, 0
    capas_sin_crs, resumen = [], []

    for ruta in geopackages:
        try:
            capas = fiona.listlayers(ruta)
            for capa_nombre in capas:
                gdf = gpd.read_file(ruta, layer=capa_nombre)
                mensaje_extra = ""

                if gdf.crs is None:
                    sin_crs += 1
                    capas_sin_crs.append(f"{ruta.stem}:{capa_nombre}")
                    if epsg_destino:
                        gdf.set_crs(epsg=epsg_destino, inplace=True)
                        mensaje_extra = f"(CRS indefinido → EPSG:{epsg_destino})"
                        QgsMessageLog.logMessage(
                            f"⚠️ {ruta.stem}:{capa_nombre} → se asignó EPSG:{epsg_destino}",
                            "GPKG Tools", Qgis.Warning
                        )
                    else:
                        gdf.set_crs(epsg=4326, inplace=True)
                        mensaje_extra = "(CRS indefinido → EPSG:4326)"
                        QgsMessageLog.logMessage(
                            f"⚠️ {ruta.stem}:{capa_nombre} → se asignó EPSG:4326",
                            "GPKG Tools", Qgis.Warning
                        )
                elif epsg_destino:
                    gdf = gdf.to_crs(epsg=epsg_destino)
                    mensaje_extra = f"(Reproyectado a EPSG:{epsg_destino})"

                ruta_relativa = ruta.relative_to(carpeta_entrada) / capa_nombre
                ruta_salida = carpeta_salida / ruta_relativa.with_suffix(".shp")
                ruta_salida.parent.mkdir(parents=True, exist_ok=True)

                gdf.to_file(ruta_salida)
                exitosos += 1
                resumen.append(f"{ruta.stem}:{capa_nombre} → exitoso {mensaje_extra}")

        except Exception as e:
            QgsMessageLog.logMessage(f"❌ {ruta.stem}: fallido → {e}", "GPKG Tools", Qgis.Critical)
            resumen.append(f"{ruta.stem}: fallido → {e}")

    # Guardar resumen
    ruta_resumen = carpeta_salida / "resumen_conversion.txt"
    with ruta_resumen.open("w", encoding="utf-8") as f:
        f.write("RESUMEN DE CONVERSIÓN DE GPKG A SHAPEFILE\n\n")
        f.write(f"Total de GPKG: {total}\n")
        f.write(f"Capas exitosas: {exitosos}\n")
        f.write(f"Capas fallidas: {total - exitosos}\n")
        f.write(f"Capas sin CRS: {sin_crs}\n\n")
        if capas_sin_crs:
            f.write("Lista de capas sin CRS:\n")
            f.write("\n".join(capas_sin_crs) + "\n\n")
        f.write("Detalle:\n" + "\n".join(resumen))

    QgsMessageLog.logMessage(f"📝 Resumen guardado en: {ruta_resumen}", "GPKG Tools", Qgis.Info)
    return ruta_resumen
