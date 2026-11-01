# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import sys

import FreeCAD
import FreeCADGui

try:
    from PySide6 import QtCore
except ImportError:
    from PySide2 import QtCore

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pdm.core.db import DatabaseManager
from pdm.core.vault import VaultEngine
from pdm.freecad.commands import register_commands
from pdm.freecad.observer import PDMDocumentObserver
from pdm.ui.dock_widget import PDMDockWidget

logger = logging.getLogger("FreeCAD-PDM.InitGui")


class PDMWorkbench(FreeCADGui.Workbench):
    MenuText = "PDM"
    ToolTip = "Product Data Management Workbench"
    Icon = os.path.join(BASE_DIR, "Resources", "icons", "pdm_workbench.svg")

    def __init__(self) -> None:
        super().__init__()
        user_pdm_dir = os.path.expanduser("~/.freecad_pdm")
        db_path = os.path.join(user_pdm_dir, "metadata.db")
        self.db_manager = DatabaseManager(db_path)
        self.vault = VaultEngine(user_pdm_dir, self.db_manager)
        self.dock_widget = None
        self.observer = PDMDocumentObserver(self.vault, on_change_callback=self._refresh_dock)

    def _refresh_dock(self) -> None:
        if self.dock_widget:
            self.dock_widget.refresh_state()

    def Initialize(self) -> None:
        cmd_list = register_commands(self.vault)
        self.appendToolbar("PDM Operations", cmd_list)
        self.appendMenu(["&PDM"], cmd_list)

        main_win = FreeCADGui.getMainWindow()
        if main_win:
            self.dock_widget = PDMDockWidget(self.vault, main_win)
            main_win.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dock_widget)

        self.observer.start()

    def Activated(self) -> None:
        if self.dock_widget:
            self.dock_widget.show()
            self.dock_widget.refresh_state()

    def Deactivated(self) -> None:
        if self.dock_widget:
            self.dock_widget.hide()

    def GetClassName(self) -> str:
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(PDMWorkbench())