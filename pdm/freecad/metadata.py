# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from typing import Any, Optional

try:
    import FreeCAD
except ImportError:
    FreeCAD = None

logger = logging.getLogger("FreeCAD-PDM.Metadata")
METADATA_OBJ_NAME = "_PDMMetadata"
PROPERTY_GROUP = "PDM Lifecycle"

class MetadataContainerProxy:
    def __init__(self, obj: Any) -> None:
        obj.Proxy = self
    def execute(self, obj: Any) -> None: pass
    def onDocumentRestored(self, obj: Any) -> None:
        obj.Proxy = self

class DocumentMetadataAdapter:
    @staticmethod
    def _get_or_create_container(doc: Any) -> Any:
        obj = doc.getObject(METADATA_OBJ_NAME)
        if obj is None:
            obj = doc.addObject("App::FeaturePython", METADATA_OBJ_NAME)
            MetadataContainerProxy(obj)
            if hasattr(obj, "Visibility"):
                obj.Visibility = False
            obj.addProperty("App::PropertyString", "PartNumber", PROPERTY_GROUP, "Part Number univoco")
            obj.addProperty("App::PropertyString", "RevisionMajor", PROPERTY_GROUP, "Revisione Major")
            obj.addProperty("App::PropertyInteger", "RevisionMinor", PROPERTY_GROUP, "Iterazione Minor")
            obj.addProperty("App::PropertyEnumeration", "State", PROPERTY_GROUP, "Stato")
            obj.State = ["WIP", "IN_REVIEW", "RELEASED", "OBSOLETE"]
            obj.addProperty("App::PropertyString", "VaultSha256", PROPERTY_GROUP, "Hash Vault")
            obj.addProperty("App::PropertyString", "LastAuthor", PROPERTY_GROUP, "Autore")
            obj.setEditorMode("VaultSha256", 1)
        return obj

    @classmethod
    def write_metadata(cls, doc: Any, part_number: str, rev_major: str, rev_minor: int, state: str, sha256: str, author: str) -> None:
        container = cls._get_or_create_container(doc)
        container.PartNumber = part_number
        container.RevisionMajor = rev_major
        container.RevisionMinor = rev_minor
        if state in container.State:
            container.State = state
        container.VaultSha256 = sha256
        container.LastAuthor = author

    @classmethod
    def read_metadata(cls, doc: Any) -> Optional[dict[str, Any]]:
        container = doc.getObject(METADATA_OBJ_NAME)
        if not container:
            return None
        return {
            "part_number": getattr(container, "PartNumber", ""),
            "revision_major": getattr(container, "RevisionMajor", ""),
            "revision_minor": getattr(container, "RevisionMinor", 0),
            "state": getattr(container, "State", "WIP"),
            "sha256": getattr(container, "VaultSha256", ""),
            "author": getattr(container, "LastAuthor", ""),
        }