# -*- coding: utf-8 -*-

from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider
from .geopacker_algorithm import GeopackerAlgorithm
import os

class GeopackerProvider(QgsProcessingProvider):

    def __init__(self):
        QgsProcessingProvider.__init__(self)

    def unload(self):
        pass

    def loadAlgorithms(self):
        self.addAlgorithm(GeopackerAlgorithm())

    def id(self):
        return 'geopacker'

    def name(self):
        return self.tr('Geopacker')

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))

    def longName(self):
        return self.name()
