# -*- coding: utf-8 -*-
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from pathlib import Path
import os

# Importar función de conversión
from .gpkg2shp_tool import convertir_gpkg_a_shp

# Importar el manejador de dependencias
from .dependency_manager import verificar_instalar_dependencias

# Cargar UI
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'gpkg2shp_dialog.ui'))

class Gpkg2ShpDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(Gpkg2ShpDialog, self).__init__(parent)
        self.setupUi(self)

        # --- Verificar dependencias antes de usar ---
        if not verificar_instalar_dependencias(self):
            self.reject()  # cerrar diálogo si el usuario no instala o falla
            return

        # Conectar botones
        self.inputBrowseButton.clicked.connect(self.select_input_file)
        self.outputBrowseButton.clicked.connect(self.select_output_folder)
        self.runButton.clicked.connect(self.run_conversion)
        self.cancelButton.clicked.connect(self.reject)

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo GPKG", "", "GeoPackage (*.gpkg);;Todos los archivos (*)")
        if file_path:
            self.inputGpkgLineEdit.setText(file_path)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de salida")
        if folder:
            self.outputFolderLineEdit.setText(folder)

    def run_conversion(self):
        input_path = Path(self.inputGpkgLineEdit.text())
        output_path = Path(self.outputFolderLineEdit.text())

        # Validaciones básicas
        if not input_path.exists() or not input_path.is_file():
            QMessageBox.warning(self, "Error", "Archivo GPKG de entrada no válido")
            return
        if not output_path.exists() or not output_path.is_dir():
            output_path.mkdir(parents=True, exist_ok=True)

        # Limpiar log
        self.logTextEdit.clear()

        try:
            convertir_gpkg_a_shp(input_path, output_path)
            self.logTextEdit.append("✅ Conversión completada")
        except Exception as e:
            self.logTextEdit.append(f"❌ Error: {e}")
