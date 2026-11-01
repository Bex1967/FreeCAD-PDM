# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from typing import Optional

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    from PySide2 import QtCore, QtWidgets

try:
    import FreeCAD
except ImportError:
    FreeCAD = None

from pdm.core.bom import BOMExtractor
from pdm.core.vault import VaultEngine, LockConflictError
from pdm.freecad.metadata import DocumentMetadataAdapter
from pdm.ui.dialogs import CheckInDialog

logger = logging.getLogger("FreeCAD-PDM.UI.Dock")

class PDMDockWidget(QtWidgets.QDockWidget):
    def __init__(self, vault: VaultEngine, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("PDM Explorer", parent)
        self.setObjectName("PDMDockWidget")
        self.vault = vault
        self._setup_ui()
        self.refresh_state()

    def _setup_ui(self) -> None:
        container = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(container)

        status_box = QtWidgets.QGroupBox("Documento Corrente")
        status_layout = QtWidgets.QFormLayout(status_box)
        self.lbl_doc_name = QtWidgets.QLabel("-")
        self.lbl_part_number = QtWidgets.QLabel("-")
        self.lbl_rev = QtWidgets.QLabel("-")
        self.lbl_lock_status = QtWidgets.QLabel("-")

        status_layout.addRow("File:", self.lbl_doc_name)
        status_layout.addRow("Part Number:", self.lbl_part_number)
        status_layout.addRow("Revisione:", self.lbl_rev)
        status_layout.addRow("Lock:", self.lbl_lock_status)
        layout.addWidget(status_box)

        actions_layout = QtWidgets.QHBoxLayout()
        self.btn_checkout = QtWidgets.QPushButton("Check-Out")
        self.btn_checkin = QtWidgets.QPushButton("Check-In")
        self.btn_undo = QtWidgets.QPushButton("Annulla Lock")
        self.btn_checkout.clicked.connect(self._on_checkout_clicked)
        self.btn_checkin.clicked.connect(self._on_checkin_clicked)
        self.btn_undo.clicked.connect(self._on_undo_clicked)
        actions_layout.addWidget(self.btn_checkout)
        actions_layout.addWidget(self.btn_checkin)
        actions_layout.addWidget(self.btn_undo)
        layout.addLayout(actions_layout)

        layout.addWidget(QtWidgets.QLabel("<b>Storico Revisioni:</b>"))
        self.table_history = QtWidgets.QTableWidget(0, 4)
        self.table_history.setHorizontalHeaderLabels(["Rev", "Stato", "Data", "Autore"])
        self.table_history.horizontalHeader().setStretchLastSection(True)
        self.table_history.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_history.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table_history)

        self.setWidget(container)

    def refresh_state(self) -> None:
        if not FreeCAD or not FreeCAD.ActiveDocument:
            self.lbl_doc_name.setText("<i>Nessun documento</i>")
            self.lbl_part_number.setText("-")
            self.lbl_rev.setText("-")
            self.lbl_lock_status.setText("-")
            self.table_history.setRowCount(0)
            self._set_buttons(False, False, False)
            return

        doc = FreeCAD.ActiveDocument
        self.lbl_doc_name.setText(doc.Label)
        meta = DocumentMetadataAdapter.read_metadata(doc)

        if not meta or not meta.get("part_number"):
            self.lbl_part_number.setText("<i>Nuovo (Non censito)</i>")
            self.lbl_rev.setText("-")
            self.lbl_lock_status.setText("-")
            self.table_history.setRowCount(0)
            self._set_buttons(False, True, False)  # Consente il primo check-in
            return

        part_num = meta["part_number"]
        self.lbl_part_number.setText(part_num)
        self.lbl_rev.setText(f"{meta['revision_major']}.{meta['revision_minor']} [{meta['state']}]")

        status = self.vault.get_lock_status(part_num)
        if status.is_locked:
            self.lbl_lock_status.setText(f"<font color='red'>Locked da {status.locked_by}</font>")
            self._set_buttons(False, True, True)
        else:
            self.lbl_lock_status.setText("<font color='green'>Disponibile</font>")
            self._set_buttons(True, False, False)

        self._load_history(part_num)

    def _set_buttons(self, co: bool, ci: bool, undo: bool) -> None:
        self.btn_checkout.setEnabled(co)
        self.btn_checkin.setEnabled(ci)
        self.btn_undo.setEnabled(undo)

    def _load_history(self, part_number: str) -> None:
        self.table_history.setRowCount(0)
        with self.vault.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.revision_major, r.revision_minor, r.state, r.created_at, r.author
                FROM revisions r
                JOIN documents d ON d.id = r.document_id
                WHERE d.part_number = ?
                ORDER BY r.id DESC
                """,
                (part_number,)
            )
            rows = cursor.fetchall()
            self.table_history.setRowCount(len(rows))
            for idx, r in enumerate(rows):
                self.table_history.setItem(idx, 0, QtWidgets.QTableWidgetItem(f"{r['revision_major']}.{r['revision_minor']}"))
                self.table_history.setItem(idx, 1, QtWidgets.QTableWidgetItem(r["state"]))
                self.table_history.setItem(idx, 2, QtWidgets.QTableWidgetItem(str(r["created_at"])[:19]))
                self.table_history.setItem(idx, 3, QtWidgets.QTableWidgetItem(r["author"]))

    def _on_checkout_clicked(self) -> None:
        doc = FreeCAD.ActiveDocument
        meta = DocumentMetadataAdapter.read_metadata(doc)
        if not meta or not meta.get("part_number"):
            return
        try:
            self.vault.check_out(meta["part_number"], doc.FileName)
            QtWidgets.QMessageBox.information(self, "Check-Out", f"Lock acquisito per {meta['part_number']}.")
        except LockConflictError as err:
            QtWidgets.QMessageBox.warning(self, "Errore Lock", str(err))
        finally:
            self.refresh_state()

    def _on_checkin_clicked(self) -> None:
        doc = FreeCAD.ActiveDocument
        if not doc.FileName:
            QtWidgets.QMessageBox.warning(self, "Attenzione", "Salva prima il file (.FCStd) su disco.")
            return

        doc.save()
        meta = DocumentMetadataAdapter.read_metadata(doc) or {}
        part_num = meta.get("part_number") or doc.Label
        rev_maj = meta.get("revision_major") or "A"
        rev_min = meta.get("revision_minor", 0)

        # Registrazione iniziale nel catalogo PDM se documento nuovo
        with self.vault.db.connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO documents (part_number, name) VALUES (?, ?);",
                (part_num, doc.Label)
            )

        dlg = CheckInDialog(part_num, rev_maj, rev_min, self)
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return

        data = dlg.get_data()
        try:
            new_rev_id = self.vault.check_in(
                part_number=part_num,
                filepath=doc.FileName,
                commit_message=data["commit_message"],
                revision_major=data["revision_major"],
                release_state=data["state"]
            )
            file_hash = self.vault.calculate_sha256(doc.FileName)
            next_minor = rev_min + 1 if data["revision_major"] == rev_maj else 0
            DocumentMetadataAdapter.write_metadata(
                doc=doc,
                part_number=part_num,
                rev_major=data["revision_major"],
                rev_minor=next_minor,
                state=data["state"],
                sha256=file_hash,
                author=meta.get("author", "")
            )

            # Estrazione e salvataggio BOM per assiemi
            bom_items = BOMExtractor.extract_from_document(doc)
            if bom_items:
                BOMExtractor.save_bom_to_vault(self.vault.db, new_rev_id, bom_items)
                BOMExtractor.export_to_freecad_spreadsheet(doc, bom_items)

            doc.save()
            QtWidgets.QMessageBox.information(self, "Successo", f"Revisione {data['revision_major']}.{next_minor} registrata nel Vault.")
        except Exception as err:
            logger.exception("Errore Check-In:")
            QtWidgets.QMessageBox.critical(self, "Errore", str(err))
        finally:
            self.refresh_state()

    def _on_undo_clicked(self) -> None:
        doc = FreeCAD.ActiveDocument
        meta = DocumentMetadataAdapter.read_metadata(doc)
        if not meta or not meta.get("part_number"):
            return
        ans = QtWidgets.QMessageBox.question(self, "Annulla Lock", "Rilasciare il lock senza salvare modifiche?")
        if ans == QtWidgets.QMessageBox.Yes:
            try:
                self.vault.undo_check_out(meta["part_number"])
            except LockConflictError as err:
                QtWidgets.QMessageBox.warning(self, "Errore", str(err))
            finally:
                self.refresh_state()