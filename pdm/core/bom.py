# -*- coding: utf-8 -*-
from __future__ import annotations
import csv
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from pdm.core.db import DatabaseManager
from pdm.freecad.metadata import DocumentMetadataAdapter

logger = logging.getLogger("FreeCAD-PDM.BOM")

@dataclass
class BOMItem:
    part_number: str
    name: str
    quantity: float
    unit: str = "pcs"
    designators: list[str] = field(default_factory=list)

class BOMExtractor:
    @classmethod
    def extract_from_document(cls, doc: Any) -> list[BOMItem]:
        if not doc:
            return []
        item_counts: dict[str, BOMItem] = {}

        for obj in doc.Objects:
            if obj.isDerivedFrom("App::Link"):
                linked_obj = getattr(obj, "LinkedObject", None)
                if not linked_obj:
                    continue
                linked_doc = linked_obj.Document
                meta = DocumentMetadataAdapter.read_metadata(linked_doc)
                part_num = meta["part_number"] if (meta and meta.get("part_number")) else linked_doc.Name
                obj_label = obj.Label

                if part_num in item_counts:
                    item_counts[part_num].quantity += 1.0
                    item_counts[part_num].designators.append(obj_label)
                else:
                    item_counts[part_num] = BOMItem(
                        part_number=part_num,
                        name=linked_doc.Label,
                        quantity=1.0,
                        unit="pcs",
                        designators=[obj_label]
                    )
            elif obj.isDerivedFrom("App::Part") and obj.getParentGeoFeatureGroup() is None:
                if obj.Name != doc.Label and not obj.InList:
                    part_num = obj.Label
                    if part_num in item_counts:
                        item_counts[part_num].quantity += 1.0
                        item_counts[part_num].designators.append(obj.Label)
                    else:
                        item_counts[part_num] = BOMItem(
                            part_number=part_num,
                            name=obj.Label,
                            quantity=1.0,
                            unit="pcs",
                            designators=[obj.Label]
                        )
        return list(item_counts.values())

    @classmethod
    def save_bom_to_vault(cls, db: DatabaseManager, parent_revision_id: int, bom_items: list[BOMItem]) -> None:
        with db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM assembly_structure WHERE parent_revision_id = ?;", (parent_revision_id,))
            for item in bom_items:
                cursor.execute("SELECT id FROM documents WHERE part_number = ?;", (item.part_number,))
                row = cursor.fetchone()
                if not row:
                    cursor.execute("INSERT INTO documents (part_number, name) VALUES (?, ?);", (item.part_number, item.name))
                    child_doc_id = cursor.lastrowid
                else:
                    child_doc_id = row["id"]

                designator_str = ", ".join(item.designators)
                cursor.execute(
                    """
                    INSERT INTO assembly_structure (parent_revision_id, child_document_id, quantity, unit, reference_designator)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (parent_revision_id, child_doc_id, item.quantity, item.unit, designator_str)
                )

    @staticmethod
    def export_to_csv(bom_items: list[BOMItem], target_path: str) -> None:
        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Part Number", "Descrizione", "Quantita", "Unita", "Riferimenti Posizione"])
            for itm in bom_items:
                writer.writerow([itm.part_number, itm.name, f"{itm.quantity:g}", itm.unit, ", ".join(itm.designators)])

    @classmethod
    def export_to_freecad_spreadsheet(cls, doc: Any, bom_items: list[BOMItem], sheet_name: str = "BOM") -> Any:
        sheet = doc.getObject(sheet_name)
        if not sheet:
            sheet = doc.addObject("Spreadsheet::Sheet", sheet_name)
        headers = ["Part Number", "Nome / Descrizione", "Quantita", "Unita", "Istanze CAD"]
        for col_idx, header in enumerate(headers, start=1):
            sheet.set(f"{chr(64 + col_idx)}1", header)
            sheet.setStyle(f"{chr(64 + col_idx)}1", "bold", "add")

        for row_idx, item in enumerate(bom_items, start=2):
            sheet.set(f"A{row_idx}", f"'{item.part_number}")
            sheet.set(f"B{row_idx}", f"'{item.name}")
            sheet.set(f"C{row_idx}", str(item.quantity))
            sheet.set(f"D{row_idx}", item.unit)
            sheet.set(f"E{row_idx}", f"'{', '.join(item.designators)}")
        doc.recompute()
        return sheet