# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import sys

import FreeCAD
import FreeCADGui

logger = logging.getLogger("FreeCAD-PDM.InitGui")


class PDMWorkbench(FreeCADGui.Workbench):
    MenuText = "PDM"
    ToolTip = "Product Data Management Workbench"
    Icon = """
    /* XPM */
    static const char *pdm_icon[] = {
    "16 16 3 1",
    "  c None",
    ". c #1B497D",
    "+ c #D13438",
    "................",
    ".              .",
    ".  ..........  .",
    ".  .        .  .",
    ".  .  ++++  .  .",
    ".  .  ++++  .  .",
    ".  .        .  .",
    ".  ..........  .",
    ".  .           .",
    ".  .           .",
    ".  .  +++++++  .",
    ".  .  +++++++  .",
    ".  .           .",
    ".  .............",
    ".              .",
    "................"
    };
    """

    def __init__(self) -> None:
        super().__init__()
        self.db_manager = None
        self.vault = None
        self.dock_widget = None
        self.observer = None

    def _resolve_addon_path(self) -> str:
        """Determina il percorso della directory del workbench."""
        possible_dirs = [
            os.path.expandvars(r"%APPDATA%\FreeCAD\v1-1\Mod\FreeCAD-PDM"),
            os.path.expandvars(r"%APPDATA%\FreeCAD\Mod\FreeCAD-PDM"),
            os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "FreeCAD-PDM"),
        ]
        for p in possible_dirs:
            if os.path.isdir(p):
                return os.path.abspath(p)
        return possible_dirs[0]

    def _refresh_dock(self) -> None:
        if self.dock_widget:
            self.dock_widget.refresh_state()

    def Initialize(self) -> None:
        """Eseguito solo quando l'utente attiva il Workbench."""
        try:
            from PySide6 import QtCore
        except ImportError:
            from PySide2 import QtCore

        # Registrazione del percorso nel sys.path
        addon_dir = self._resolve_addon_path()
        if addon_dir not in sys.path:
            sys.path.insert(0, addon_dir)

        from pdm.core.db import DatabaseManager
        from pdm.core.vault import VaultEngine
        from pdm.freecad.commands import register_commands
        from pdm.freecad.observer import PDMDocumentObserver
        from pdm.ui.dock_widget import PDMDockWidget

        user_pdm_dir = os.path.expanduser("~/.freecad_pdm")
        db_path = os.path.join(user_pdm_dir, "metadata.db")
        self.db_manager = DatabaseManager(db_path)
        self.vault = VaultEngine(user_pdm_dir, self.db_manager)

        # Toolbar e Menu
        cmd_list = register_commands(self.vault)
        self.appendToolbar("PDM Operations", cmd_list)
        self.appendMenu(["&PDM"], cmd_list)

        # Dock Widget
        main_win = FreeCADGui.getMainWindow()
        if main_win:
            self.dock_widget = PDMDockWidget(self.vault, main_win)
            main_win.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dock_widget)

        # Observer
        self.observer = PDMDocumentObserver(self.vault, on_change_callback=self._refresh_dock)
        self.observer.start()

        FreeCAD.Console.PrintMessage("[PDM] Workbench attivato con successo.\n")

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
1
