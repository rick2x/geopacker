# -*- coding: utf-8 -*-
import sys
import os
import shutil
import subprocess
import site
import importlib

from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QMessageBox, QApplication


def _get_python_executable():
    """Locate the Python executable used by the current QGIS installation."""
    exe = sys.executable
    base = os.path.basename(exe).lower()
    if base in ("python.exe", "python3.exe", "python", "python3"):
        return exe

    # On Windows, sys.executable often points to qgis-bin.exe or qgis-ltr-bin.exe
    exe_dir = os.path.dirname(exe)
    for name in ("python.exe", "python3.exe", "python", "python3"):
        candidate = os.path.join(exe_dir, name)
        if os.path.isfile(candidate):
            return candidate

    # Check OSGeo4W root if available
    osgeo_root = os.environ.get("OSGEO4W_ROOT")
    if osgeo_root:
        candidate = os.path.join(osgeo_root, "bin", "python.exe")
        if os.path.isfile(candidate):
            return candidate
        apps_dir = os.path.join(osgeo_root, "apps")
        if os.path.isdir(apps_dir):
            for entry in os.listdir(apps_dir):
                if entry.lower().startswith("python"):
                    p = os.path.join(apps_dir, entry, "python.exe")
                    if os.path.isfile(p):
                        return p

    # Fallback to PATH search
    which_py = shutil.which("python") or shutil.which("python3")
    if which_py:
        return which_py

    return sys.executable


def _install_defusedxml():
    """
    Attempts to install defusedxml via pip in the background.
    First tries standard installation, then falls back to user site-packages (--user).
    Returns (success: bool, error_message: str).
    """
    py_exe = _get_python_executable()
    env = os.environ.copy()
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    # 1. Try standard pip install
    proc = subprocess.run(
        [py_exe, "-m", "pip", "install", "defusedxml"],
        env=env,
        capture_output=True,
        text=True,
        creationflags=flags
    )

    # 2. If standard install fails (e.g. permission denied in Program Files), try --user
    if proc.returncode != 0:
        proc = subprocess.run(
            [py_exe, "-m", "pip", "install", "--user", "defusedxml"],
            env=env,
            capture_output=True,
            text=True,
            creationflags=flags
        )

    if proc.returncode == 0:
        # Ensure user site-packages directory is in sys.path
        try:
            user_site = site.getusersitepackages()
            if user_site and os.path.isdir(user_site) and user_site not in sys.path:
                sys.path.insert(0, user_site)
        except Exception:
            pass

        importlib.invalidate_caches()
        try:
            import defusedxml  # noqa: F401
            return True, ""
        except ImportError as e:
            return False, f"Package installed successfully but could not be imported: {e}"
    else:
        err = proc.stderr.strip() or proc.stdout.strip() or f"Process exited with code {proc.returncode}"
        return False, err


def _show_manual_instructions(parent=None, error_msg=None):
    """
    Displays step-by-step manual installation instructions for defusedxml.
    Provides an option to copy the pip install command.
    """
    cmd_text = "pip install defusedxml"

    box = QMessageBox(parent)
    icon_crit = getattr(QMessageBox, "Icon", QMessageBox).Critical
    icon_info = getattr(QMessageBox, "Icon", QMessageBox).Information
    box.setIcon(icon_crit if error_msg else icon_info)
    box.setWindowTitle("Manual Installation Instructions")

    text_format = getattr(Qt, "TextFormat", Qt).RichText
    interaction = getattr(Qt, "TextInteractionFlag", Qt).TextBrowserInteraction
    box.setTextFormat(text_format)
    box.setTextInteractionFlags(interaction)

    if error_msg:
        header = (
            "<h3 style='color: #c0392b;'>Automatic Installation Failed</h3>"
            "<p>Geopacker was unable to install <b>'defusedxml'</b> automatically. "
            "Please install it manually using the instructions below:</p><hr>"
        )
    else:
        header = (
            "<h3>Manual Installation Instructions</h3>"
            "<p>To protect against potential XML vulnerabilities during project packaging, "
            "Geopacker requires the <b>'defusedxml'</b> library.</p><hr>"
        )

    msg = (
        f"{header}"
        "<h4>Windows (OSGeo4W Shell)</h4>"
        "<ol>"
        "<li>Close QGIS.</li>"
        "<li>Open the Windows Start Menu and search for <b>OSGeo4W Shell</b>.</li>"
        "<li>Right-click and choose <b>Run as Administrator</b>.</li>"
        f"<li>Type or paste: <code>{cmd_text}</code> and press Enter.</li>"
        "<li>Restart QGIS and reopen Geopacker.</li>"
        "</ol>"
        "<h4>Linux / macOS</h4>"
        "<ul>"
        "<li><b>Linux (Debian/Ubuntu):</b> <code>sudo apt install python3-defusedxml</code> or <code>pip install defusedxml</code></li>"
        "<li><b>macOS:</b> <code>pip3 install defusedxml</code></li>"
        "</ul>"
    )
    box.setText(msg)

    if error_msg:
        box.setDetailedText(f"Installation error details:\n\n{error_msg}")

    role_action = getattr(QMessageBox, "ButtonRole", QMessageBox).ActionRole
    btn_copy = box.addButton("Copy Command", role_action)
    btn_close = box.addButton(getattr(QMessageBox, "StandardButton", QMessageBox).Close)

    while True:
        if hasattr(box, "exec"):
            box.exec()
        else:
            box.exec_()

        clicked = box.clickedButton()
        if clicked == btn_copy:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(cmd_text)
            btn_copy.setText("Copied to Clipboard!")
            continue
        else:
            break


def check_and_install_dependencies(parent=None, feedback=None):
    """
    Checks if required dependencies (defusedxml) are installed.
    If missing, prompts the user to install it automatically or view manual instructions.
    Returns True if dependencies are available, False otherwise.
    """
    try:
        import defusedxml  # noqa: F401
        return True
    except ImportError:
        pass

    # Handle PyQt5 and PyQt6 enum scoping
    icon_question = getattr(QMessageBox, "Icon", QMessageBox).Question
    icon_information = getattr(QMessageBox, "Icon", QMessageBox).Information
    btn_ok = getattr(QMessageBox, "StandardButton", QMessageBox).Ok
    role_accept = getattr(QMessageBox, "ButtonRole", QMessageBox).AcceptRole
    role_action = getattr(QMessageBox, "ButtonRole", QMessageBox).ActionRole
    role_reject = getattr(QMessageBox, "ButtonRole", QMessageBox).RejectRole
    text_format = getattr(Qt, "TextFormat", Qt).RichText
    cursor_wait = getattr(Qt, "CursorShape", Qt).WaitCursor

    app = QApplication.instance()

    # Headless / CLI execution check
    is_headless = parent is None and (app is None or not hasattr(app, "activeWindow") or app.activeWindow() is None)
    if is_headless:
        msg = "defusedxml is not installed. Attempting automatic installation..."
        if feedback:
            feedback.pushInfo(msg)
        QgsMessageLog.logMessage(msg, "Geopacker", Qgis.Info)

        success, err = _install_defusedxml()
        if success:
            success_msg = "defusedxml installed successfully."
            if feedback:
                feedback.pushInfo(success_msg)
            QgsMessageLog.logMessage(
                success_msg,
                "Geopacker",
                Qgis.Success if hasattr(Qgis, "Success") else Qgis.Info
            )
            return True
        else:
            fail_msg = (
                f"Failed to install defusedxml automatically: {err}\n"
                f"Manual install: open OSGeo4W Shell as Admin and run 'pip install defusedxml'"
            )
            if feedback:
                feedback.reportError(fail_msg)
            QgsMessageLog.logMessage(fail_msg, "Geopacker", Qgis.Critical)
            return False

    # Interactive GUI prompt
    prompt_box = QMessageBox(parent)
    prompt_box.setIcon(icon_question)
    prompt_box.setWindowTitle("Geopacker Dependency Required")
    prompt_box.setTextFormat(text_format)
    prompt_box.setText(
        "<h3>Geopacker Security Dependency</h3>"
        "<p>To protect against potential XML vulnerabilities during project packaging, "
        "Geopacker requires the <b>'defusedxml'</b> library.</p>"
        "<p>Would you like Geopacker to automatically install <b>defusedxml</b> now via pip?</p>"
    )

    btn_auto = prompt_box.addButton("Install Automatically", role_accept)
    btn_manual = prompt_box.addButton("Manual Instructions", role_action)
    btn_cancel = prompt_box.addButton("Cancel", role_reject)
    prompt_box.setDefaultButton(btn_auto)

    if hasattr(prompt_box, "exec"):
        prompt_box.exec()
    else:
        prompt_box.exec_()

    clicked = prompt_box.clickedButton()
    if clicked == btn_manual:
        _show_manual_instructions(parent=parent)
        return False
    elif clicked != btn_auto:
        return False

    # Show waiting cursor during installation
    if app:
        app.setOverrideCursor(cursor_wait)
        app.processEvents()

    try:
        success, err = _install_defusedxml()
    finally:
        if app:
            app.restoreOverrideCursor()

    if success:
        success_box = QMessageBox(parent)
        success_box.setIcon(icon_information)
        success_box.setWindowTitle("Installation Complete")
        success_box.setTextFormat(text_format)
        success_box.setText(
            "<h3>Installation Successful</h3>"
            "<p>The <b>'defusedxml'</b> library was successfully installed and loaded.</p>"
            "<p>Geopacker is ready to package your project.</p>"
        )
        success_box.setStandardButtons(btn_ok)
        if hasattr(success_box, "exec"):
            success_box.exec()
        else:
            success_box.exec_()
        return True
    else:
        # Automatic installation failed -> show detailed manual instructions with the error details
        _show_manual_instructions(parent=parent, error_msg=err)
        return False
