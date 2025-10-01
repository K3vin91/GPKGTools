# -*- coding: utf-8 -*-
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from pathlib import Path
from .gpkg2fusion_tool import fusionar_vectores
import os

# Cargar el UI
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'gpkg2fusion_dialog.ui'))

class Gpkg2FusionDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(Gpkg2FusionDialog, self).__init__(parent)
        self.setupUi(self)

        # Conectar botones
        self.inputBrowseButton.clicked.connect(self.select_input_folder)
        self.outputBrowseButton.clicked.connect(self.select_output_file)
        self.runButton.clicked.connect(self.run_fusion)
        self.cancelButton.clicked.connect(self.reject)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de entrada")
        if folder:
            self.inputFolderLineEdit.setText(folder)

    def select_output_file(self):
        # Permite elegir archivo GPKG de salida o carpeta
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Seleccionar archivo GPKG de salida",
            "",
            "GeoPackage (*.gpkg);;Todos los archivos (*)"
        )
        if path:
            self.outputGpkgLineEdit.setText(path)

    def run_fusion(self):
        input_path = Path(self.inputFolderLineEdit.text().strip())
        output_path = Path(self.outputGpkgLineEdit.text().strip())
        epsg_text = self.epsgLineEdit.text().strip()

        # Validaciones básicas
        if not input_path.exists() or not input_path.is_dir():
            QMessageBox.warning(self, "Error", "Carpeta de entrada no válida")
            return
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)

        epsg = None
        if epsg_text:
            if not epsg_text.isdigit():
                QMessageBox.warning(self, "Error", "EPSG debe ser un número válido")
                return
            epsg = int(epsg_text)

        # Limpiar log
        self.logTextEdit.clear()

        try:
            gpkg_result, resumen_path = fusionar_vectores(input_path, output_path, epsg_destino=epsg)
            self.logTextEdit.append(f"✅ Fusión completada.\nArchivo GPKG: {gpkg_result}\nResumen guardado en: {resumen_path}")
        except Exception as e:
            self.logTextEdit.append(f"❌ Error: {e}")
