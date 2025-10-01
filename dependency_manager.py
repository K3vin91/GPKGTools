# -*- coding: utf-8 -*-
import sys
import subprocess
from qgis.PyQt.QtWidgets import QMessageBox

def verificar_instalar_dependencias(parent=None):
    """
    Verifica si geopandas y fiona están instalados.
    Si falta alguna, intenta instalarla usando pip del Python de QGIS.
    """
    paquetes = ["geopandas", "fiona"]
    faltantes = []

    for pkg in paquetes:
        try:
            __import__(pkg)
        except ImportError:
            faltantes.append(pkg)

    if not faltantes:
        return True  # Todo OK

    # Preguntar al usuario si desea instalar
    respuesta = QMessageBox.question(
        parent,
        "Instalar dependencias",
        f"Faltan las siguientes librerías: {', '.join(faltantes)}.\n"
        "¿Desea que el plugin las instale automáticamente?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    )

    if respuesta != QMessageBox.Yes:
        return False

    try:
        python_exe = sys.executable
        subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade"] + faltantes)
        QMessageBox.information(parent, "Instalación completada",
                                "Las librerías faltantes se instalaron correctamente.\n"
                                "Reinicie QGIS si es necesario.")
        return True
    except Exception as e:
        QMessageBox.critical(parent, "Error instalación",
                             f"No se pudieron instalar las librerías: {e}")
        return False
