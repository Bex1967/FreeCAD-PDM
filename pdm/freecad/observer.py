# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from typing import Any, Callable, Optional

try:
    import FreeCAD
except ImportError:
    FreeCAD = None

from pdm.core.vault import VaultEngine
from pdm.freecad.metadata import DocumentMetadataAdapter

logger = logging.getLogger("FreeCAD-PDM.Observer")

class PDMDocumentObserver:
    def __init__(self, vault: VaultEngine, on_change_callback: Optional[Callable[[], None]] = None) -> None:
        self.vault = vault
        self.on_change_callback = on_change_callback
        self._is_active = False

    def start(self) -> None:
        if FreeCAD and not self._is_active:
            FreeCAD.addDocumentObserver(self)
            self._is_active = True

    def stop(self) -> None:
        if FreeCAD and self._is_active:
            FreeCAD.removeDocumentObserver(self)
            self._is_active = False

    def _notify(self) -> None:
        if self.on_change_callback:
            self.on_change_callback()

    def slotCreatedDocument(self, doc: Any) -> None: self._notify()
    def slotDeletedDocument(self, doc: Any) -> None: self._notify()
    def slotSavedDocument(self, doc: Any) -> None: self._notify()

    def slotOpenDocument(self, doc: Any) -> None:
        self._notify()
        meta = DocumentMetadataAdapter.read_metadata(doc)
        if meta and meta.get("part_number"):
            status = self.vault.get_lock_status(meta["part_number"])
            if status.is_locked:
                FreeCAD.Console.PrintWarning(f"[PDM] File in Check-Out da '{status.locked_by}'.\n")

    def slotBeforeSaveDocument(self, doc: Any, save_path: str) -> None:
        meta = DocumentMetadataAdapter.read_metadata(doc)
        if meta and meta.get("part_number"):
            status = self.vault.get_lock_status(meta["part_number"])
            if not status.is_locked:
                FreeCAD.Console.PrintWarning(f"[PDM] ATTENZIONE: Salvataggio di '{meta['part_number']}' senza Lock attivo.\n")