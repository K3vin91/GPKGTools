# -*- coding: utf-8 -*-
import os
from pathlib import Path
import geopandas as gpd
import fiona
from pyproj import CRS
from qgis.core import Qgis, QgsMessageLog

def leer_capa(ruta, capa=None, epsg_destino=None, capas_sin_crs=None):
    """Lee una capa de un archivo vectorial y reproyecta si es necesario."""
    gdf = gpd.read_file(ruta, layer=capa) if capa else gpd.read_file(ruta)
    if gdf.empty:
        return None
    if gdf.crs is None and capas_sin_crs is not None:
        capas_sin_crs.append(capa or Path(ruta).stem)
    if epsg_destino:
        gdf = gdf.to_crs(epsg=epsg_destino)
    return gdf

def obtener_nombre_unico(base, existentes):
    """Genera nombre único evitando duplicados en el GPKG de salida."""
    nombre = base
    i = 1
    while nombre in existentes:
        nombre = f"{base}_{i}"
        i += 1
    existentes.add(nombre)
    return nombre

def procesar_gpkg(ruta, salida, epsg_destino, capas_existentes, resumen, capas_sin_crs):
    """Procesa todas las capas de un GPKG."""
    for capa in fiona.listlayers(ruta):
        try:
            gdf = leer_capa(ruta, capa, epsg_destino, capas_sin_crs)
            if gdf is None:
                msg = f"⚠️ {ruta} -> {capa}: vacía, ignorada"
                resumen.append(msg)
                QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Warning)
                continue
            archivo_base = Path(ruta).stem
            nombre_capa = obtener_nombre_unico(f"{archivo_base}_{capa}", capas_existentes)
            gdf.to_file(salida, layer=nombre_capa, driver="GPKG", mode="a")
            msg = f"✅ {ruta} -> {capa}: exportada como {nombre_capa}"
            resumen.append(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info)
        except Exception as e:
            msg = f"❌ {ruta} -> {capa}: falló → {e}"
            resumen.append(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)

def procesar_vector_simple(ruta, salida, epsg_destino, capas_existentes, resumen, capas_sin_crs):
    """Procesa shapefile o geojson individual."""
    try:
        gdf = leer_capa(ruta, epsg_destino=epsg_destino, capas_sin_crs=capas_sin_crs)
        if gdf is None:
            msg = f"⚠️ {ruta}: vacío, ignorado"
            resumen.append(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Warning)
            return
        archivo_base = Path(ruta).stem
        nombre_capa = obtener_nombre_unico(archivo_base, capas_existentes)
        gdf.to_file(salida, layer=nombre_capa, driver="GPKG", mode="a")
        msg = f"✅ {ruta}: exportado como {nombre_capa}"
        resumen.append(msg)
        QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info)
    except Exception as e:
        msg = f"❌ {ruta}: falló → {e}"
        resumen.append(msg)
        QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)

def fusionar_vectores(carpeta, salida, epsg_destino=None):
    """Fusiona todos los vectores en un único GPKG y genera resumen TXT."""
    carpeta = Path(carpeta)
    salida = Path(salida)

    # Validar EPSG
    if epsg_destino:
        epsg_destino = int(epsg_destino)
        CRS.from_epsg(epsg_destino)  # valida que exista

    # Si la salida es carpeta, crear archivo fusion.gpkg
    if salida.is_dir() or salida.suffix.lower() != ".gpkg":
        salida.mkdir(parents=True, exist_ok=True)
        salida = salida / "fusion.gpkg"

    # Borrar si existe
    if salida.exists():
        salida.unlink()

    capas_existentes = set()
    resumen = []
    capas_sin_crs = []
    total, exitosos, fallidos = 0, 0, 0

    for file in carpeta.rglob("*"):
        if file.is_file():
            ext = file.suffix.lower()
            total += 1
            if ext == ".gpkg":
                procesar_gpkg(file, salida, epsg_destino, capas_existentes, resumen, capas_sin_crs)
                exitosos += 1
            elif ext in [".shp", ".geojson"]:
                procesar_vector_simple(file, salida, epsg_destino, capas_existentes, resumen, capas_sin_crs)
                exitosos += 1
            else:
                msg = f"⚠️ {file}: formato no soportado, ignorado"
                resumen.append(msg)
                QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Warning)
                fallidos += 1

    # Guardar resumen
    resumen_path = salida.with_name(salida.stem + "_resumen.txt")
    with open(resumen_path, "w", encoding="utf-8") as f:
        f.write("RESUMEN DE FUSIÓN DE VECTORES EN GPKG\n\n")
        f.write(f"Carpeta procesada: {carpeta}\n")
        f.write(f"Archivo de salida: {salida}\n\n")
        f.write(f"Total de capas procesadas: {total}\n")
        if capas_sin_crs:
            f.write(f"Capas sin CRS (requieren reproyección): {len(capas_sin_crs)}\n")
            f.write("\n".join(capas_sin_crs) + "\n")
        f.write(f"\nCapas exitosas: {exitosos}\n")
        f.write(f"Archivos ignorados/fallidos: {fallidos}\n")

    QgsMessageLog.logMessage(f"✅ Fusión completada en: {salida}", "GPKG Tools", Qgis.Info)
    QgsMessageLog.logMessage(f"📝 Resumen guardado en: {resumen_path}", "GPKG Tools", Qgis.Info)
    return salida, resumen_path
