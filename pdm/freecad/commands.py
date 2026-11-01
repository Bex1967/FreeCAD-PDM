# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
import os
from typing import Optional

try:
    import FreeCAD
    import FreeCADGui
    from PySide6 import QtWidgets
except ImportError:
    FreeCAD = None
    FreeCADGui = None
    from PySide2 import QtWidgets

from pdm.core.bom import BOMExtractor
from pdm.core.vault import VaultEngine

logger = logging.getLogger("FreeCAD-PDM.Commands")
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ICON_DIR = os.path.join(BASE_DIR, "Resources", "icons")

class PDMCommandCheckIn:
    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": os.path.join(ICON_DIR, "checkin.svg"),
            "MenuText": "Check-In Documento...",
            "ToolTip": "Salva e registra una nuova revisione nel Vault",
            "Accel": "Ctrl+Shift+I",
        }
    def IsActive(self) -> bool:
        return bool(FreeCAD and FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.FileName)
    def Activated(self) -> None:
        mw = FreeCADGui.getMainWindow()
        dock = mw.findChild(QtWidgets.QDockWidget, "PDMDockWidget") if mw else None
        if dock and hasattr(dock, "_on_checkin_clicked"):
            dock._on_checkin_clicked()

class PDMCommandCheckOut:
    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": os.path.join(ICON_DIR, "checkout.svg"),
            "MenuText": "Check-Out Documento",
            "ToolTip": "Acquisisce il Lock per modificare il file",
            "Accel": "Ctrl+Shift+O",
        }
    def IsActive(self) -> bool:
        return bool(FreeCAD and FreeCAD.ActiveDocument and FreeCAD.ActiveDocument.FileName)
    def Activated(self) -> None:
        mw = FreeCADGui.getMainWindow()
        dock = mw.findChild(QtWidgets.QDockWidget, "PDMDockWidget") if mw else None
        if dock and hasattr(dock, "_on_checkout_clicked"):
            dock._on_checkout_clicked()

class PDMCommandExportBOM:
    def GetResources(self) -> dict[str, str]:
        return {
            "Pixmap": os.path.join(ICON_DIR, "bom.svg"),
            "MenuText": "Esporta Distinta Base (BOM)...",
            "ToolTip": "Genera ed esporta la distinta base in formato CSV",
            "Accel": "Ctrl+Shift+B",
        }
    def IsActive(self) -> bool:
        return bool(FreeCAD and FreeCAD.ActiveDocument)
    def Activated(self) -> None:
        doc = FreeCAD.ActiveDocument
        bom_items = BOMExtractor.extract_from_document(doc)
        if not bom_items:
            FreeCAD.Console.PrintWarning("[PDM] Nessun componente o assieme valido per la BOM.\n")
            return
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, "Esporta Distinta Base", f"{doc.Label}_BOM.csv", "File CSV (*.csv)"
        )
        if file_path:
            BOMExtractor.export_to_csv(bom_items, file_path)
            FreeCAD.Console.PrintMessage(f"[PDM] Distinta esportata in: {file_path}\n")

def register_commands(vault: Optional[VaultEngine] = None) -> list[str]:
    if not FreeCADGui:
        return []
    commands = {
        "PDM_CheckIn": PDMCommandCheckIn(),
        "PDM_CheckOut": PDMCommandCheckOut(),
        "PDM_ExportBOM": PDMCommandExportBOM(),
    }
    for name, cmd in commands.items():
        FreeCADGui.addCommand(name, cmd)
    return list(commands.keys())