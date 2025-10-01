# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GpkgTools
                                 A QGIS plugin
 Es un complemento diseñado para simplificar el manejo de GeoPackages
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from . import resources

import os.path

class GpkgTools:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr(u'&GPKG Tools')
        self.toolbar = self.iface.addToolBar("GPKG Tools")
        self.toolbar.setObjectName("GPKGTools")

        # Traducción
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(
            self.plugin_dir, "i18n", f"GpkgTools_{locale}.qm"
        )
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    def tr(self, message):
        """Traducción."""
        return QCoreApplication.translate("GpkgTools", message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        parent=None,
        add_to_toolbar=True,
        add_to_menu=True,
    ):
        """Añadir acción a la barra de herramientas y menú."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Inicializa GUI del plugin con los 3 botones."""
        # Botón SHP → GPKG
        self.add_action(
            ":/plugins/gpkg_tools/icon_shp2gpkg.png",
            text=self.tr("SHP → GPKG"),
            callback=self.run_shp2gpkg,
            parent=self.iface.mainWindow(),
        )

        # Botón GPKG → SHP
        self.add_action(
            ":/plugins/gpkg_tools/icon_gpkg2shp.png",
            text=self.tr("GPKG → SHP"),
            callback=self.run_gpkg2shp,
            parent=self.iface.mainWindow(),
        )

        # Botón Fusionar a GPKG
        self.add_action(
            ":/plugins/gpkg_tools/icon_gpkg2fusion.png",
            text=self.tr("Fusionar a GPKG"),
            callback=self.run_gpkg2fusion,
            parent=self.iface.mainWindow(),
        )

    def unload(self):
        """Quitar menú y toolbar al desinstalar plugin."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr("&GPKG Tools"), action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    # ---- Callbacks para los diálogos ----
    def run_shp2gpkg(self):
        from .shp2gpkg_dialog import Shp2GpkgDialog
        dlg = Shp2GpkgDialog()
        dlg.exec_()

    def run_gpkg2shp(self):
        from .gpkg2shp_dialog import Gpkg2ShpDialog
        dlg = Gpkg2ShpDialog()
        dlg.exec_()

    def run_gpkg2fusion(self):
        from .gpkg2fusion_dialog import Gpkg2FusionDialog
        dlg = Gpkg2FusionDialog()
        dlg.exec_()

