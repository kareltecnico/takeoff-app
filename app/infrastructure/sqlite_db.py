from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SqliteDb:
    path: Path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row

        # IMPORTANT: SQLite does NOT enforce foreign keys unless enabled per connection.
        conn.execute("PRAGMA foreign_keys = ON")

        _migrate(conn)
        return conn


def _migrate(conn: sqlite3.Connection) -> None:
    # Idempotent schema creation (safe to run on every startup).

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            internal_item_code TEXT NOT NULL UNIQUE,
            lennar_item_number TEXT NULL,
            description1 TEXT NOT NULL,
            description2 TEXT NULL,
            unit_price TEXT NOT NULL,
            default_taxable INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT NOT NULL UNIQUE,
            project_name TEXT NOT NULL,
            contractor_name TEXT NULL,
            foreman TEXT NULL,
            status TEXT NOT NULL DEFAULT 'in_course',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            template_code TEXT PRIMARY KEY,
            template_name TEXT NOT NULL,
            category TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS template_lines (
            template_code TEXT NOT NULL,
            item_code TEXT NOT NULL,
            qty TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (template_code, item_code),
            FOREIGN KEY (template_code) REFERENCES templates(template_code) ON DELETE CASCADE,
            FOREIGN KEY (item_code) REFERENCES items(internal_item_code)
        )
        """
    )

    # -------------------------
    # Takeoffs (snapshot)
    # -------------------------
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS takeoffs (
            takeoff_id TEXT PRIMARY KEY,
            project_code TEXT NOT NULL,
            template_code TEXT NOT NULL,
            tax_rate TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_code) REFERENCES projects(project_code) ON DELETE RESTRICT,
            FOREIGN KEY (template_code) REFERENCES templates(template_code) ON DELETE RESTRICT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS takeoff_lines (
            takeoff_id TEXT NOT NULL,
            item_code TEXT NOT NULL,
            qty TEXT NOT NULL,
            notes TEXT,

            -- SNAPSHOT FIELDS (do not depend on live catalog later)
            description_snapshot TEXT NOT NULL,
            details_snapshot TEXT NULL,
            unit_price_snapshot TEXT NOT NULL,
            taxable_snapshot INTEGER NOT NULL,

            -- Optional future fields (kept for later phases)
            stage TEXT NULL,
            factor TEXT NOT NULL DEFAULT '1',
            sort_order INTEGER NOT NULL DEFAULT 0,

            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),

            PRIMARY KEY (takeoff_id, item_code),
            FOREIGN KEY (takeoff_id) REFERENCES takeoffs(takeoff_id) ON DELETE CASCADE,
            FOREIGN KEY (item_code) REFERENCES items(internal_item_code)
        )
        """
    )

    conn.commit()