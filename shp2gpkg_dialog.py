# -*- coding: utf-8 -*-
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.core import QgsTask, QgsMessageLog, Qgis, QgsApplication
from pathlib import Path
import os

from .shp2gpkg_tool import convertir_shapefiles

# Cargar UI
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'shp2gpkg_dialog.ui'))

class Shp2GpkgDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # Conectar botones
        self.inputBrowseButton.clicked.connect(self.select_input_folder)
        self.outputBrowseButton.clicked.connect(self.select_output_folder)
        self.runButton.clicked.connect(self.run_conversion)
        self.cancelButton.clicked.connect(self.cancel_task)

        self.task = None

        # Mensaje inicial en log
        self.logTextEdit.append(
            "🗂️ Reporte de capas convertidas de Shapefiles a GPKG"
        )

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de entrada")
        if folder:
            self.inputFolderLineEdit.setText(folder)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de salida")
        if folder:
            self.outputFolderLineEdit.setText(folder)

    def run_conversion(self):
        input_path = Path(self.inputFolderLineEdit.text())
        output_path = Path(self.outputFolderLineEdit.text())
        epsg_text = self.epsgLineEdit.text().strip()

        # Validaciones
        if not input_path.exists() or not input_path.is_dir():
            QMessageBox.warning(self, "Error", "Carpeta de entrada no válida")
            return
        if not output_path.exists() or not output_path.is_dir():
            output_path.mkdir(parents=True, exist_ok=True)

        epsg = int(epsg_text) if epsg_text.isdigit() else None

        # Limpiar log
        self.logTextEdit.clear()
        self.logTextEdit.append("▶ Iniciando conversión de Shapefiles a GPKG...")

        # Deshabilitar botón mientras se procesa
        self.runButton.setEnabled(False)

        # Crear tarea y pasar referencia al diálogo
        self.task = ShpToGpkgTask(input_path, output_path, epsg, self.logTextEdit, self)
        QgsApplication.taskManager().addTask(self.task)

    def cancel_task(self):
        # Solo cancelar si la tarea aún existe
        if self.task:
            self.task.cancel()
            self.logTextEdit.append("⏹ Cancelando tarea...")

# ----------------------------------------------------
class ShpToGpkgTask(QgsTask):
    def __init__(self, input_path, output_path, epsg, log_widget, dialog):
        super().__init__("Convertir SHP a GPKG")
        self.input_path = input_path
        self.output_path = output_path
        self.epsg = epsg
        self.log_widget = log_widget
        self.dialog = dialog
        self.cancelled_flag = False

    def cancel(self):
        self.cancelled_flag = True
        return super().cancel()

    def run(self):
        # Callback para cancelar
        def cancel_cb():
            return self.cancelled_flag

        # Callback para logs
        def log_cb(msg):
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info)
            if self.log_widget:
                self.log_widget.append(msg)

        try:
            convertir_shapefiles(
                self.input_path,
                self.output_path,
                epsg_destino=self.epsg,
                cancel_callback=cancel_cb,
                log_callback=log_cb
            )
        except Exception as e:
            log_cb(f"❌ Error inesperado: {e}")
        return True

    def finished(self, result):
        if self.log_widget:
            self.log_widget.append("✅ Tarea finalizada.")
        # Rehabilitar botón de manera segura
        if self.dialog and hasattr(self.dialog, "runButton"):
            self.dialog.runButton.setEnabled(True)
            # Limpiar referencia a la tarea para evitar errores al presionar "Cancelar"
            self.dialog.task = None
