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
        # Auto-update estimate when any filter checkbox changes
        self.chkStripDuplicates.toggled.connect(self._update_estimate)
        self.chkStripEmpty.toggled.connect(self._update_estimate)
        self.chkSkipRemoteVectors.toggled.connect(self._update_estimate)
        self.chkOnlySelected.toggled.connect(self._update_estimate)
        self.chkRetainFullFiltered.toggled.connect(self._update_estimate)

    # ------------------------------------------------------------------ #
    #  Estimated Output Size                                               #
    # ------------------------------------------------------------------ #
    def showEvent(self, event):
        """Auto-calculate the estimate every time the dialog is shown."""
        super().showEvent(event)
        self._update_estimate()

    def _update_estimate(self):
        """Run the estimator and update the label with a breakdown."""
        from .packaging_logic import GeopackerLogic

        try:
            est = GeopackerLogic.estimate_project_size(
                strip_duplicates=self.chkStripDuplicates.isChecked(),
                strip_empty=self.chkStripEmpty.isChecked(),
                skip_remote=self.chkSkipRemoteVectors.isChecked(),
                only_selected=self.chkOnlySelected.isChecked(),
                retain_full_filtered=self.chkRetainFullFiltered.isChecked(),
            )
        except Exception as e:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(
                f"Estimate failed: {e}", "Geopacker", Qgis.Warning
            )
            self.lblEstimatedSize.setText(
                "Estimated Output Size: (unable to calculate)")
            return

        total = est['total']
        if total == 0:
            self.lblEstimatedSize.setText(
                f"Estimated Output Size: 0 B — {est['layer_count']} layer(s)"
            )
            self.lblEstimatedSize.setStyleSheet(
                "font-weight: bold; color: #7F8C8D; font-size: 9pt;"
            )
            return

        # Build category breakdown
        import math

        def _fmt(b):
            if b == 0:
                return '0 B'
            units = ('B', 'KB', 'MB', 'GB', 'TB')
            i = int(math.floor(math.log(b, 1024)))
            p = math.pow(1024, i)
            return f'{round(b / p, 2)} {units[i]}'

        parts = []
        if est['vectors'] > 0:
            parts.append(f"Vectors: {_fmt(est['vectors'])}")
        if est['rasters'] > 0:
            parts.append(f"Rasters: {_fmt(est['rasters'])}")
        if est['styles'] > 0:
            parts.append(f"Styles: {_fmt(est['styles'])}")
        if est['project'] > 0:
            parts.append(f"Project: {_fmt(est['project'])}")

        breakdown = " | ".join(parts)
        text = f"Estimated Output Size: ~{est['formatted']}"
        if breakdown:
            text += f"  ({breakdown})"
        text += f" — {est['layer_count']} layer(s)"

        # Color: red for ≥ 10 GB, orange for ≥ 1 GB, teal for normal
        if total >= 10 * 1024 ** 3:
            color = "#C0392B"
        elif total >= 1 * 1024 ** 3:
            color = "#D35400"
        else:
            color = "#16A085"

        self.lblEstimatedSize.setText(text)
        self.lblEstimatedSize.setStyleSheet(
            f"font-weight: bold; color: {color}; font-size: 9pt;"
        )

    def run_packaging(self):
        from .packaging_logic import GeopackerLogic
        output_file = self.fileOutput.filePath()
        strip_dupes = self.chkStripDuplicates.isChecked()
        strip_empty = self.chkStripEmpty.isChecked()
        skip_remote = self.chkSkipRemoteVectors.isChecked()
        only_selected = self.chkOnlySelected.isChecked()
        group_gpkgs = self.chkGroupGpkgs.isChecked()
        retain_full_filtered = self.chkRetainFullFiltered.isChecked()

        if not output_file:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Error", "Please select an output zip file.")
            return

        logic = GeopackerLogic(
            output_file=output_file,
            strip_duplicates=strip_dupes,
            strip_empty=strip_empty,
            skip_remote=skip_remote,
            only_selected=only_selected,
            group_gpkgs=group_gpkgs,
            retain_full_filtered=retain_full_filtered,
            progress_bar=self.progressBar,
            status_label=self.lblStatus
        )
        try:
            failed_layers = logic.run()
            from qgis.PyQt.QtWidgets import QMessageBox
            if failed_layers:
                msg = "Packaging completed, but the following layers failed or were skipped:\n" + \
                    "\n".join(failed_layers)
                QMessageBox.warning(self, "Partial Success",
                                    f"Project packaged to {output_file}\n\n{msg}")
            else:
                QMessageBox.information(
                    self, "Success", f"Project packaged successfully to {output_file}")
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
            QMessageBox.critical(
                self, "Error", f"Failed to package project:\n{str(e)}")
