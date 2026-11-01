# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional

try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets

class CheckInDialog(QtWidgets.QDialog):
    def __init__(self, part_number: str, current_major: str, current_minor: int, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"PDM - Check-In [{part_number}]")
        self.setMinimumWidth(440)
        self.part_number = part_number
        self.current_major = current_major or "A"
        self.current_minor = current_minor
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        info_group = QtWidgets.QGroupBox("Revisione")
        info_layout = QtWidgets.QFormLayout(info_group)

        self.lbl_part = QtWidgets.QLabel(f"<b>{self.part_number}</b>")
        self.lbl_current_rev = QtWidgets.QLabel(f"{self.current_major}.{self.current_minor}")
        info_layout.addRow("Part Number:", self.lbl_part)
        info_layout.addRow("Revisione Attuale:", self.lbl_current_rev)

        self.combo_bump = QtWidgets.QComboBox()
        next_major = chr(ord(self.current_major) + 1) if (len(self.current_major) == 1 and self.current_major.isalpha()) else "B"
        self.combo_bump.addItem(f"Iterazione Minor ({self.current_major}.{self.current_minor + 1})", "minor")
        self.combo_bump.addItem(f"Nuova Major Release ({next_major}.0)", "major")
        info_layout.addRow("Incremento:", self.combo_bump)

        self.combo_state = QtWidgets.QComboBox()
        self.combo_state.addItems(["WIP", "IN_REVIEW", "RELEASED", "OBSOLETE"])
        info_layout.addRow("Stato:", self.combo_state)
        layout.addWidget(info_group)

        commit_group = QtWidgets.QGroupBox("Note di Revisione")
        commit_layout = QtWidgets.QVBoxLayout(commit_group)
        self.txt_commit = QtWidgets.QPlainTextEdit()
        self.txt_commit.setPlaceholderText("Descrivi le modifiche...")
        commit_layout.addWidget(self.txt_commit)
        layout.addWidget(commit_group)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.btn_ok = btn_box.button(QtWidgets.QDialogButtonBox.Ok)
        self.btn_ok.setText("Esegui Check-In")
        self.btn_ok.setEnabled(False)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.txt_commit.textChanged.connect(lambda: self.btn_ok.setEnabled(bool(self.txt_commit.toPlainText().strip())))

    def get_data(self) -> dict[str, str]:
        bump_type = self.combo_bump.currentData()
        next_major = chr(ord(self.current_major) + 1) if (len(self.current_major) == 1 and self.current_major.isalpha()) else "B"
        rev_major = next_major if bump_type == "major" else self.current_major
        return {
            "revision_major": rev_major,
            "state": self.combo_state.currentText(),
            "commit_message": self.txt_commit.toPlainText().strip(),
        }