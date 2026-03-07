# -*- coding: utf-8 -*-
import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'geopacker_dialog_base.ui'))

class GeopackerDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(GeopackerDialog, self).__init__(parent)
        self.setupUi(self)
        
        # Connect signals
        self.btnRun.clicked.connect(self.run_packaging)
        self.btnCancel.clicked.connect(self.close)

    def run_packaging(self):
        from .packaging_logic import GeopackerLogic
        output_file = self.fileOutput.filePath()
        strip_dupes = self.chkStripDuplicates.isChecked()
        strip_empty = self.chkStripEmpty.isChecked()
        skip_remote = self.chkSkipRemoteVectors.isChecked()
        only_selected = self.chkOnlySelected.isChecked()
        group_gpkgs = self.chkGroupGpkgs.isChecked()
        
        if not output_file:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", "Please select an output zip file.")
            return
            
        logic = GeopackerLogic(
            output_file=output_file, 
            strip_duplicates=strip_dupes, 
            strip_empty=strip_empty,
            skip_remote=skip_remote,
            only_selected=only_selected,
            group_gpkgs=group_gpkgs,
            progress_bar=self.progressBar,
            status_label=self.lblStatus
        )
        try:
            failed_layers = logic.run()
            from qgis.PyQt.QtWidgets import QMessageBox
            if failed_layers:
                msg = "Packaging completed, but the following layers failed or were skipped:\n" + "\n".join(failed_layers)
                QMessageBox.warning(self, "Partial Success", f"Project packaged to {output_file}\n\n{msg}")
            else:
                QMessageBox.information(self, "Success", f"Project packaged successfully to {output_file}")
            self.accept()
        except Exception as e:
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception as cleanup_err:
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(
                        f"Failed to clean up partial output file: {cleanup_err}",
                        "Geopacker", Qgis.Warning
                    )
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to package project:\n{str(e)}")
