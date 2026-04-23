# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessingAlgorithm,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterBoolean,
                       QgsProject)

from .packaging_logic import GeopackerLogic

class GeopackerAlgorithm(QgsProcessingAlgorithm):
    """
    Geopacker QGIS Processing Algorithm for headless execution.
    """

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    STRIP_DUPLICATES = 'STRIP_DUPLICATES'
    STRIP_EMPTY = 'STRIP_EMPTY'
    SKIP_REMOTE = 'SKIP_REMOTE'
    ONLY_SELECTED = 'ONLY_SELECTED'
    GROUP_GPKGS = 'GROUP_GPKGS'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return GeopackerAlgorithm()

    def name(self):
        return 'package_project'

    def displayName(self):
        return self.tr('Package Project')

    def group(self):
        return ''

    def groupId(self):
        return ''

    def shortHelpString(self):
        return self.tr("Packages a QGIS project and its layers into a portable ZIP file.")

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                self.tr('Input QGIS Project (.qgz) (Optional: leave empty to use current)'),
                optional=True,
                extension='qgz',
                behavior=QgsProcessingParameterFile.File
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.STRIP_DUPLICATES,
                self.tr('Strip Duplicate Data Sources'),
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.STRIP_EMPTY,
                self.tr('Strip Empty Temporary Scratch Layers'),
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.SKIP_REMOTE,
                self.tr('Skip Remote Connections (e.g., PostGIS, WFS)'),
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ONLY_SELECTED,
                self.tr('Only export selected features (if any are selected)'),
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GROUP_GPKGS,
                self.tr('Group GPKGs by their Layer Tree hierarchy'),
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Output ZIP File'),
                fileFilter='ZIP files (*.zip)'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        # Check for dependencies
        from .dependency_manager import check_and_install_dependencies
        # Use QgsMessageLog via feedback if parent is not available
        if not check_and_install_dependencies():
            return {}

        input_project_path = self.parameterAsFile(parameters, self.INPUT, context)
        output_zip_path = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        
        strip_duplicates = self.parameterAsBool(parameters, self.STRIP_DUPLICATES, context)
        strip_empty = self.parameterAsBool(parameters, self.STRIP_EMPTY, context)
        skip_remote = self.parameterAsBool(parameters, self.SKIP_REMOTE, context)
        only_selected = self.parameterAsBool(parameters, self.ONLY_SELECTED, context)
        group_gpkgs = self.parameterAsBool(parameters, self.GROUP_GPKGS, context)

        # Load the project
        project = QgsProject.instance()
        if input_project_path:
            feedback.pushInfo(f"Loading project from {input_project_path}")
            project = QgsProject()
            if not project.read(input_project_path):
                feedback.reportError(f"Failed to load project from {input_project_path}")
                return {}
        
        # Initialize and run logic
        logic = GeopackerLogic(
            output_file=output_zip_path,
            strip_duplicates=strip_duplicates,
            strip_empty=strip_empty,
            skip_remote=skip_remote,
            only_selected=only_selected,
            group_gpkgs=group_gpkgs,
            project=project,
            feedback=feedback
        )
        
        failed_layers = logic.run()

        if failed_layers:
            feedback.pushWarning("Some layers failed to package. Check the generated report in the output ZIP.")

        return {self.OUTPUT: output_zip_path}
