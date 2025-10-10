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

def procesar_gpkg(gpkg_path, salida_ds, capas_existentes, resumen, log_cb=None, cancel_cb=None):
    """Copia todas las capas de un GPKG de entrada al GeoPackage de salida usando OGR.CopyLayer."""
    try:
        in_ds = ogr.Open(str(gpkg_path))
        if not in_ds:
            msg = f"❌ {gpkg_path.name}: GPKG no válido"
            resumen.append(msg)
            if log_cb: log_cb(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)
            return

        for i in range(in_ds.GetLayerCount()):
            if cancel_cb and cancel_cb():
                if log_cb:
                    log_cb("⏹ Cancelación detectada, deteniendo fusión...")
                return

            in_layer = in_ds.GetLayerByIndex(i)
            nombre_capa = in_layer.GetName()
            if in_layer.GetFeatureCount() == 0:
                msg = f"⚠️ {gpkg_path.name} → {nombre_capa}: vacía, ignorada"
                resumen.append(msg)
                if log_cb: log_cb(msg)
                QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Warning)
                continue

            nombre_capa_salida = obtener_nombre_unico(f"{gpkg_path.stem}_{nombre_capa}", capas_existentes)

            # Copiar la capa completa al GPKG de salida
            out_layer = salida_ds.CopyLayer(in_layer, nombre_capa_salida)
            if out_layer:
                msg = f"✅ {gpkg_path.name} → {nombre_capa} copiada como {nombre_capa_salida}"
            else:
                msg = f"❌ {gpkg_path.name} → {nombre_capa} no pudo copiarse"
            resumen.append(msg)
            if log_cb: log_cb(msg)
            QgsMessageLog.logMessage(msg, "GPKG Tools",
                                     Qgis.Info if out_layer else Qgis.Critical)

    except Exception as e:
        msg = f"❌ {gpkg_path.name}: error durante la fusión → {e}"
        resumen.append(msg)
        if log_cb: log_cb(msg)
        QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)
    finally:
        in_ds = None

def fusionar_vectores(carpeta, salida, log_cb=None, cancel_cb=None):
    """Fusiona todos los GPKG de una carpeta en un único GPKG usando GDAL/OGR (optimizado)."""
    carpeta = Path(carpeta)
    salida = Path(salida)

    if salida.is_dir() or salida.suffix.lower() != ".gpkg":
        salida.mkdir(parents=True, exist_ok=True)
        salida = salida / "fusion.gpkg"

    if salida.exists():
        salida.unlink()

    driver = ogr.GetDriverByName("GPKG")
    out_ds = driver.CreateDataSource(str(salida))
    if out_ds is None:
        raise RuntimeError(f"No se pudo crear el GeoPackage de salida: {salida}")

    capas_existentes = set()
    resumen = []
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
                procesar_gpkg(file, out_ds, capas_existentes, resumen, log_cb, cancel_cb)
                procesados += 1
            except Exception as e:
                msg = f"❌ {file.name}: error durante la fusión → {e}"
                resumen.append(msg)
                if log_cb: log_cb(msg)
                QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Critical)
                fallidos += 1

    # Guardar resumen
    resumen_path = salida.with_name(salida.stem + "_resumen.txt")
    try:
        with open(resumen_path, "w", encoding="utf-8") as f:
            f.write("📘 RESUMEN DE FUSIÓN DE GPKG\n\n")
            f.write(f"📂 Carpeta procesada: {carpeta}\n")
            f.write(f"💾 Archivo de salida: {salida}\n\n")
            f.write(f"Total de archivos GPKG procesados: {total_archivos}\n")
            f.write(f"Archivos fusionados correctamente: {procesados}\n")
            f.write(f"Archivos con errores: {fallidos}\n\n")
            f.write("\n--- Detalle de ejecución ---\n")
            f.write("\n".join(resumen))
    except Exception as e:
        if log_cb: log_cb(f"❌ Error guardando resumen: {e}")
        QgsMessageLog.logMessage(f"❌ Error guardando resumen: {e}", "GPKG Tools", Qgis.Critical)

    if log_cb:
        log_cb(f"✅ Fusión completada en: {salida}")
        log_cb(f"📝 Resumen guardado en: {resumen_path}")

    QgsMessageLog.logMessage(f"✅ Fusión completada en: {salida}", "GPKG Tools", Qgis.Info)
    QgsMessageLog.logMessage(f"📝 Resumen guardado en: {resumen_path}", "GPKG Tools", Qgis.Info)

    out_ds = None
    return salida, resumen_path
