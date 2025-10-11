# -*- coding: utf-8 -*-
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import QgsTask, QgsMessageLog, Qgis, QgsApplication
from pathlib import Path
from .gpkg2fusion_tool import fusionar_vectores
import os

# Cargar el UI
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'gpkg2fusion_dialog.ui'))


class LoggerEmitter(QObject):
    """Objeto que emite señales de log para ser conectadas al QTextEdit en el hilo GUI."""
    signal = pyqtSignal(str)


class Gpkg2FusionDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._log_emitter = LoggerEmitter()
        self._log_emitter.signal.connect(self._append_log_threadsafe)

        # Conectar botones
        self.inputBrowseButton.clicked.connect(self.select_input_folder)
        self.outputBrowseButton.clicked.connect(self.select_output_file)
        self.runButton.clicked.connect(self.run_fusion)
        self.cancelButton.clicked.connect(self.cancel_task)

        self.task = None
        self.task_active = False
        self.logTextEdit.append("📦 Herramienta de fusión de GPKG")

    def _append_log_threadsafe(self, msg: str):
        self.logTextEdit.append(msg)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de entrada")
        if folder:
            self.inputFolderLineEdit.setText(folder)

    def select_output_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Seleccionar archivo GPKG de salida",
            "",
            "GeoPackage (*.gpkg);;Todos los archivos (*)"
        )
        if path and not path.lower().endswith(".gpkg"):
            path += ".gpkg"
        if path:
            self.outputFileLineEdit.setText(path)

    def run_fusion(self):
        # Leer entradas
        input_text = self.inputFolderLineEdit.text().strip()
        output_text = self.outputFileLineEdit.text().strip()

        # Validaciones
        if not input_text:
            QMessageBox.warning(self, "Error", "Debe seleccionar una carpeta de entrada.")
            return
        if not output_text:
            QMessageBox.warning(self, "Error", "Debe seleccionar un archivo de salida (.gpkg).")
            return

        input_path = Path(input_text)
        output_path = Path(output_text)

        if not input_path.exists() or not input_path.is_dir():
            QMessageBox.warning(self, "Error", "La carpeta de entrada no es válida.")
            return

        if not output_path.parent.exists():
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo crear la carpeta de salida:\n{e}")
                return

        # Limpiar log
        self.logTextEdit.clear()
        self.logTextEdit.append("📦 Iniciando proceso de fusión...\n")

        # Crear tarea y agregar al task manager
        self.task = GpkgToFusionTask(
            input_path,
            output_path,
            log_emitter=self._log_emitter,
            dialog=self
        )
        self.task_active = True
        self.runButton.setEnabled(False)
        QgsApplication.taskManager().addTask(self.task)

    def cancel_task(self):
        if self.task_active and self.task:
            self.task.cancel()
            self.logTextEdit.append("⏹ Cancelando tarea...")


# ----------------------------------------------------
class GpkgToFusionTask(QgsTask):
    def __init__(self, input_path, output_path, log_emitter: LoggerEmitter, dialog):
        super().__init__("Fusión de GPKG")
        self.input_path = input_path
        self.output_path = output_path
        self.log_emitter = log_emitter
        self.dialog = dialog
        self.cancelled_flag = False

    def cancel(self):
        self.cancelled_flag = True
        return super().cancel()

    def run(self):
        def cancel_cb():
            return self.cancelled_flag

        def log_cb(msg):
            QgsMessageLog.logMessage(msg, "GPKG Tools", Qgis.Info)
            if self.log_emitter:
                self.log_emitter.signal.emit(msg)

        try:
            fusionar_vectores(
                self.input_path,
                self.output_path,
                log_cb=log_cb,
                cancel_cb=cancel_cb
            )
        except Exception as e:
            log_cb(f"❌ Error durante la fusión: {e}")

        return True

    def finished(self, result):
        if self.dialog:
            self.dialog.task_active = False
            if hasattr(self.dialog, "runButton"):
                self.dialog.runButton.setEnabled(True)
        if self.log_emitter:
            self.log_emitter.signal.emit("✅ Tarea finalizada.")
