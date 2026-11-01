# -*- coding: utf-8 -*-
from __future__ import annotations
import getpass
import hashlib
import logging
import os
import platform
import shutil
from dataclasses import dataclass
from typing import Optional
from pdm.core.db import DatabaseManager

logger = logging.getLogger("FreeCAD-PDM.Vault")

class PDMError(Exception): pass
class LockConflictError(PDMError): pass
class DocumentNotFoundError(PDMError): pass

@dataclass(frozen=True)
class CheckOutStatus:
    is_locked: bool
    locked_by: Optional[str] = None
    locked_at: Optional[str] = None
    working_copy_path: Optional[str] = None

class VaultEngine:
    def __init__(self, vault_root: str, db_manager: DatabaseManager) -> None:
        self.vault_root = os.path.abspath(vault_root)
        self.storage_dir = os.path.join(self.vault_root, "objects")
        self.db = db_manager
        os.makedirs(self.storage_dir, exist_ok=True)

    @staticmethod
    def calculate_sha256(filepath: str) -> str:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                hasher.update(block)
        return hasher.hexdigest()

    def get_lock_status(self, part_number: str) -> CheckOutStatus:
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.user_name, c.locked_at, c.working_copy_path
                FROM checkouts c
                JOIN documents d ON d.id = c.document_id
                WHERE d.part_number = ?
                """,
                (part_number,)
            )
            row = cursor.fetchone()
            if row:
                return CheckOutStatus(
                    is_locked=True,
                    locked_by=row["user_name"],
                    locked_at=str(row["locked_at"]),
                    working_copy_path=row["working_copy_path"]
                )
            return CheckOutStatus(is_locked=False)

    def check_out(self, part_number: str, working_copy_path: str, user_name: Optional[str] = None) -> None:
        user = user_name or getpass.getuser()
        hostname = platform.node()
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM documents WHERE part_number = ?;", (part_number,))
            doc_row = cursor.fetchone()
            if not doc_row:
                raise DocumentNotFoundError(f"Part Number '{part_number}' non trovato.")
            doc_id = doc_row["id"]

            cursor.execute("SELECT user_name, locked_at FROM checkouts WHERE document_id = ?;", (doc_id,))
            lock_row = cursor.fetchone()
            if lock_row:
                raise LockConflictError(f"File bloccato da '{lock_row['user_name']}'.")

            cursor.execute(
                """
                INSERT INTO checkouts (document_id, user_name, hostname, working_copy_path)
                VALUES (?, ?, ?, ?);
                """,
                (doc_id, user, hostname, os.path.abspath(working_copy_path))
            )

    def undo_check_out(self, part_number: str, force: bool = False, current_user: Optional[str] = None) -> None:
        user = current_user or getpass.getuser()
        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.document_id, c.user_name 
                FROM checkouts c
                JOIN documents d ON d.id = c.document_id
                WHERE d.part_number = ?
                """,
                (part_number,)
            )
            row = cursor.fetchone()
            if not row:
                return
            if not force and row["user_name"] != user:
                raise LockConflictError(f"Non puoi annullare il lock di {row['user_name']}.")
            cursor.execute("DELETE FROM checkouts WHERE document_id = ?;", (row["document_id"],))

    def check_in(
        self,
        part_number: str,
        filepath: str,
        commit_message: str,
        revision_major: str,
        author: Optional[str] = None,
        release_state: str = "WIP"
    ) -> int:
        user = author or getpass.getuser()
        file_hash = self.calculate_sha256(filepath)
        file_size = os.path.getsize(filepath)

        with self.db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM documents WHERE part_number = ?;", (part_number,))
            doc_row = cursor.fetchone()
            if not doc_row:
                raise DocumentNotFoundError(f"Part Number '{part_number}' non censito.")
            doc_id = doc_row["id"]

            cursor.execute("SELECT user_name FROM checkouts WHERE document_id = ?;", (doc_id,))
            lock_row = cursor.fetchone()
            if lock_row and lock_row["user_name"] != user:
                raise LockConflictError(f"Check-In respinto: lock di '{lock_row['user_name']}'.")

            cursor.execute(
                """
                SELECT COALESCE(MAX(revision_minor), -1) + 1 AS next_minor
                FROM revisions
                WHERE document_id = ? AND revision_major = ?;
                """,
                (doc_id, revision_major)
            )
            next_minor = cursor.fetchone()["next_minor"]

            dest_subdir = os.path.join(self.storage_dir, file_hash[:2], file_hash[2:4])
            os.makedirs(dest_subdir, exist_ok=True)
            dest_filepath = os.path.join(dest_subdir, f"{file_hash}.FCStd")
            rel_storage_path = os.path.relpath(dest_filepath, self.vault_root)

            if not os.path.exists(dest_filepath):
                shutil.copy2(filepath, dest_filepath)
                os.chmod(dest_filepath, 0o444)

            cursor.execute(
                """
                INSERT INTO revisions (
                    document_id, revision_major, revision_minor, state,
                    sha256, file_size, storage_path, commit_message, author
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (doc_id, revision_major, next_minor, release_state, file_hash, file_size, rel_storage_path, commit_message, user)
            )
            new_rev_id = cursor.lastrowid
            cursor.execute("DELETE FROM checkouts WHERE document_id = ?;", (doc_id,))
            return new_rev_id