# -*- coding: utf-8 -*-
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.core import QgsTask, QgsMessageLog, Qgis, QgsApplication
from pathlib import Path
import os

# Función principal de conversión
from .gpkg2shp_tool import convertir_gpkg_a_shp

# Cargar UI
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'gpkg2shp_dialog.ui'))

class Gpkg2ShpDialog(QDialog, FORM_CLASS):
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
        self.logTextEdit.append("🗂️ Reporte de capas extraídas de GPKG a Shapefiles")

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
        self.logTextEdit.append("▶ Iniciando extracción de GPKG a Shapefiles...")

        # Deshabilitar botón mientras se procesa
        self.runButton.setEnabled(False)

        # Crear tarea
        self.task = GpkgToShpTask(input_path, output_path, epsg, self.logTextEdit, self)
        QgsApplication.taskManager().addTask(self.task)

    def cancel_task(self):
        if self.task:
            self.task.cancel()
            self.logTextEdit.append("⏹ Cancelando tarea...")

# ----------------------------------------------------
class GpkgToShpTask(QgsTask):
    def __init__(self, input_path, output_path, epsg, log_widget, dialog):
        super().__init__("Extraer GPKG a SHP")
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
        # Callback para cancelación
        def cancel_cb():
            return self.cancelled_flag

        # Callback para logs
        def log_cb(msg):
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info)
            if self.log_widget:
                self.log_widget.append(msg)

        try:
            convertir_gpkg_a_shp(
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
        # Evitar errores si la tarea fue cancelada
        if self.cancelled_flag:
            if self.log_widget:
                self.log_widget.append("⏹ Tarea cancelada por el usuario.")
        else:
            if self.log_widget:
                self.log_widget.append("✅ Tarea finalizada.")
        # Rehabilitar botón de forma segura
        if self.dialog and hasattr(self.dialog, "runButton"):
            self.dialog.runButton.setEnabled(True)
