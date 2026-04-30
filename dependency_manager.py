# -*- coding: utf-8 -*-
import sys
import os
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox

def check_and_install_dependencies(parent=None):
    """
    Checks if required dependencies (defusedxml) are installed.
    If not, provides manual installation instructions with a Google Drive link.
    Returns True if dependencies are available, False otherwise.
    """
    try:
        import defusedxml
        return True
    except ImportError:
        drive_link = "https://drive.google.com/file/d/1N_ZH5FGswiRzNG-Ojwflbsdfa22fJ0YE/view?usp=sharing"
        
        msg = (
            "<h3>Geopacker 1.5 Security Update</h3>"
            "<p>To protect against potential XML vulnerabilities, Geopacker now requires the <b>'defusedxml'</b> library.</p>"
            "<p>This library was not detected. Please install it manually to continue:</p>"
            "<ol>"
            "<li>Close QGIS.</li>"
            "<li>Open the <b>OSGeo4W Shell</b> as Administrator.</li>"
            "<li>Run: <code>pip install defusedxml</code></li>"
            "<li>Restart QGIS.</li>"
            "</ol>"
            f"<p><b>Visual Guide:</b><br>"
            f"<a href='{drive_link}'>Watch the installation guide on Google Drive</a></p>"
        )
        
        box = QMessageBox(parent)
        
        # Handle PyQt6 enum changes (scoping)
        icon = getattr(QMessageBox, 'Icon', QMessageBox).Critical
        button = getattr(QMessageBox, 'StandardButton', QMessageBox).Ok
        text_format = getattr(Qt, 'TextFormat', Qt).RichText
        interaction = getattr(Qt, 'TextInteractionFlag', Qt).TextBrowserInteraction

        box.setIcon(icon)
        box.setWindowTitle("Dependency Missing")
        box.setTextFormat(text_format)
        box.setText(msg)
        box.setStandardButtons(button)
        # This flag makes the links clickable
        box.setTextInteractionFlags(interaction)
        
        if hasattr(box, 'exec'):
            box.exec()
        else:
            box.exec_()
        
        return False
