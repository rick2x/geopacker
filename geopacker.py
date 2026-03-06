# -*- coding: utf-8 -*-
import os
import sys

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsApplication

from .geopacker_dialog import GeopackerDialog
from .geopacker_provider import GeopackerProvider

class Geopacker:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # Declare instance attributes
        self.actions = []
        self.menu = u'&Geopacker'
        self.toolbar = self.iface.addToolBar(u'Geopacker')
        self.toolbar.setObjectName(u'Geopacker')
        self.dlg = None
        self.provider = None

    def initProcessing(self):
        self.provider = GeopackerProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.initProcessing()
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=u'Geopacker',
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            
        for action in self.actions:
            self.iface.removePluginMenu(u'&Geopacker', action)
            self.iface.removeToolBarIcon(action)
        
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        if self.dlg is None:
            self.dlg = GeopackerDialog()
            self.dlg.btnHelp.clicked.connect(self.show_help)

        self.dlg.show()
        result = self.dlg.exec_()
        
        if result:
            pass
            
    def show_help(self):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://github.com/rick2x/geopacker/blob/main/README.md"))
