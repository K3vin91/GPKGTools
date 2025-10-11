# -*- coding: utf-8 -*-
from pathlib import Path
from osgeo import ogr
from qgis.core import QgsMessageLog, Qgis

def obtener_nombre_unico(base, existentes):
    """Genera un nombre único basado en 'base' que no exista en 'existentes'."""
    nombre = base
    i = 1
    while nombre in existentes:
        nombre = f"{base}_{i}"
        i += 1
    existentes.add(nombre)
    return nombre

def abrir_gpkg(path):
    ds = ogr.Open(str(path))
    if not ds:
        raise RuntimeError(f"No se pudo abrir: {path}")
    return ds

def copiar_capa(in_layer, out_ds, nombre_capa):
    """Copia la capa sin reproyectar, retorna el EPSG original de la capa."""
    srs = in_layer.GetSpatialRef()
    epsg = srs.GetAttrValue("AUTHORITY", 1) if srs else "Sin CRS"
    out_layer = out_ds.CopyLayer(in_layer, nombre_capa)
    if not out_layer:
        raise RuntimeError(f"Error copiando capa {nombre_capa}")
    return out_layer, epsg

def procesar_gpkg(ruta, out_ds, capas_existentes, resumen, capas_sin_crs, log_cb=None, cancel_cb=None):
    """Procesa todas las capas de un GPKG y las añade al GPKG de salida."""
    in_ds = abrir_gpkg(ruta)
    for i in range(in_ds.GetLayerCount()):
        if cancel_cb and cancel_cb():
            if log_cb:
                log_cb("⏹ Cancelación detectada, deteniendo fusión...")
            return

        in_layer = in_ds.GetLayerByIndex(i)
        if in_layer.GetFeatureCount() == 0:
            msg = f"⚠️ {ruta.name} → {in_layer.GetName()}: vacía, ignorada"
            resumen.append(msg)
            if log_cb: log_cb(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Warning)
            continue

        nombre_capa_salida = obtener_nombre_unico(f"{ruta.stem}_{in_layer.GetName()}", capas_existentes)
        try:
            out_layer, epsg = copiar_capa(in_layer, out_ds, nombre_capa_salida)
            msg = f"✅ {ruta.name} → {nombre_capa_salida} fusionada (EPSG: {epsg})"
            resumen.append(msg)
            if not epsg or epsg == "None":
                capas_sin_crs.append(nombre_capa_salida)
            if log_cb: log_cb(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info)
        except Exception as e:
            msg = f"❌ {ruta.name} → {nombre_capa_salida}: {e}"
            resumen.append(msg)
            if log_cb: log_cb(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)
            capas_sin_crs.append(nombre_capa_salida)

def generar_resumen(salida, carpeta, resumen, capas_sin_crs, total_archivos, procesados, fallidos):
    resumen_path = salida.with_name(salida.stem + "_resumen.txt")
    with open(resumen_path, "w", encoding="utf-8") as f:
        f.write("📘 RESUMEN DE FUSIÓN DE GPKG\n\n")
        f.write(f"📂 Carpeta procesada: {carpeta}\n")
        f.write(f"💾 Archivo de salida: {salida}\n\n")
        f.write(f"Total de archivos GPKG procesados: {total_archivos}\n")
        f.write(f"Archivos fusionados correctamente: {procesados}\n")
        f.write(f"Archivos con errores: {fallidos}\n\n")
        if capas_sin_crs:
            f.write("⚠️ Capas sin CRS detectadas:\n")
            f.write("\n".join(capas_sin_crs) + "\n")
        f.write("\n--- Detalle de ejecución ---\n")
        f.write("\n".join(resumen))
    return resumen_path

def fusionar_vectores(carpeta, salida, log_cb=None, cancel_cb=None):
    """Fusiona todos los GPKG de una carpeta y sus subcarpetas en un único GPKG."""
    carpeta = Path(carpeta)
    salida = Path(salida)

    if salida.is_dir() or salida.suffix.lower() != ".gpkg":
        salida.mkdir(parents=True, exist_ok=True)
        salida = salida / "fusion.gpkg"
    if salida.exists():
        salida.unlink()

    driver = ogr.GetDriverByName("GPKG")
    out_ds = driver.CreateDataSource(str(salida))
    if not out_ds:
        raise RuntimeError(f"No se pudo crear el GeoPackage de salida: {salida}")

    resumen = []
    capas_existentes = set()
    capas_sin_crs = []
    total_archivos = procesados = fallidos = 0

    for file in carpeta.rglob("*.gpkg"):
        if cancel_cb and cancel_cb():
            if log_cb: log_cb("⏹ Cancelación detectada, deteniendo fusión...")
            break
        if not file.is_file():
            continue

        total_archivos += 1
        try:
            procesar_gpkg(file, out_ds, capas_existentes, resumen, capas_sin_crs, log_cb, cancel_cb)
            procesados += 1
        except Exception as e:
            msg = f"❌ {file.name}: {e}"
            resumen.append(msg)
            if log_cb: log_cb(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)
            fallidos += 1

    resumen_path = generar_resumen(salida, carpeta, resumen, capas_sin_crs, total_archivos, procesados, fallidos)

    if log_cb:
        log_cb(f"✅ Fusión completada en: {salida}")
        log_cb(f"📝 Resumen guardado en: {resumen_path}")
    QgsMessageLog.logMessage(f"✅ Fusión completada en: {salida}", "GPKG Tools", Qgis.Info)
    QgsMessageLog.logMessage(f"📝 Resumen guardado en: {resumen_path}", "GPKG Tools", Qgis.Info)

    out_ds = None
    return salida, resumen_path
