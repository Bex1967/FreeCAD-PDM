# -*- coding: utf-8 -*-
from __future__ import annotations
import contextlib
import logging
import os
import sqlite3
from typing import Generator

logger = logging.getLogger("FreeCAD-PDM.Database")
SCHEMA_VERSION = 1

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_info (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    revision_major TEXT NOT NULL,
    revision_minor INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'WIP',
    sha256 TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    commit_message TEXT,
    author TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(document_id, revision_major, revision_minor)
);

CREATE TABLE IF NOT EXISTS checkouts (
    document_id INTEGER PRIMARY KEY,
    user_name TEXT NOT NULL,
    hostname TEXT,
    working_copy_path TEXT NOT NULL,
    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lease_expires_at TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assembly_structure (
    parent_revision_id INTEGER NOT NULL,
    child_document_id INTEGER NOT NULL,
    quantity REAL NOT NULL DEFAULT 1.0,
    unit TEXT NOT NULL DEFAULT 'pcs',
    reference_designator TEXT,
    PRIMARY KEY(parent_revision_id, child_document_id),
    FOREIGN KEY(parent_revision_id) REFERENCES revisions(id) ON DELETE CASCADE,
    FOREIGN KEY(child_document_id) REFERENCES documents(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_revisions_doc ON revisions(document_id);
CREATE INDEX IF NOT EXISTS idx_revisions_sha ON revisions(sha256);
CREATE INDEX IF NOT EXISTS idx_docs_part_number ON documents(part_number);
"""


class DatabaseManager:
    def __init__(self, db_path: str) -> None:
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextlib.contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_schema(self) -> None:
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(SCHEMA_SQL)
            cursor.execute("SELECT MAX(version) FROM schema_info;")
            row = cursor.fetchone()
            current_ver = row[0] if (row and row[0] is not None) else 0
            if current_ver < SCHEMA_VERSION:
                cursor.execute("INSERT INTO schema_info (version) VALUES (?);", (SCHEMA_VERSION,))