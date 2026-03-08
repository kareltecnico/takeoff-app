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


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(r["name"]) == column for r in rows)


def _migrate(conn: sqlite3.Connection) -> None:
    """Idempotent schema creation + additive migrations.

    Safe to run on every startup.
    """

    # -------------------------
    # Catalog / Master data
    # -------------------------
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
            valve_discount TEXT NOT NULL DEFAULT '0.00',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    # Additive migrations for projects
    if not _has_column(conn, "projects", "valve_discount"):
        conn.execute(
            "ALTER TABLE projects ADD COLUMN valve_discount TEXT NOT NULL DEFAULT '0.00'"
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

            -- TemplateLine v2
            stage TEXT NOT NULL DEFAULT 'final',
            factor TEXT NOT NULL DEFAULT '1.0',
            sort_order INTEGER NOT NULL DEFAULT 0,

            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (template_code, item_code),
            FOREIGN KEY (template_code) REFERENCES templates(template_code) ON DELETE CASCADE,
            FOREIGN KEY (item_code) REFERENCES items(internal_item_code)
        )
        """
    )

    # Additive migrations for DBs created before TemplateLine v2.
    if not _has_column(conn, "template_lines", "stage"):
        conn.execute("ALTER TABLE template_lines ADD COLUMN stage TEXT NOT NULL DEFAULT 'final'")
    if not _has_column(conn, "template_lines", "factor"):
        conn.execute("ALTER TABLE template_lines ADD COLUMN factor TEXT NOT NULL DEFAULT '1.0'")
    if not _has_column(conn, "template_lines", "sort_order"):
        conn.execute("ALTER TABLE template_lines ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")

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
            valve_discount TEXT NOT NULL DEFAULT '0.00',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_code) REFERENCES projects(project_code) ON DELETE RESTRICT,
            FOREIGN KEY (template_code) REFERENCES templates(template_code) ON DELETE RESTRICT
        )
        """
    )

    if not _has_column(conn, "takeoffs", "valve_discount"):
        conn.execute(
            "ALTER TABLE takeoffs ADD COLUMN valve_discount TEXT NOT NULL DEFAULT '0.00'"
        )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS takeoff_lines (
            takeoff_id TEXT NOT NULL,
            item_code TEXT NOT NULL,
            qty TEXT NOT NULL,
            notes TEXT NULL,

            -- SNAPSHOT FIELDS (do not depend on live catalog later)
            description_snapshot TEXT NOT NULL,
            details_snapshot TEXT NULL,
            unit_price_snapshot TEXT NOT NULL,
            taxable_snapshot INTEGER NOT NULL,

            -- TemplateLine v2 fields (persisted on snapshot lines)
            stage TEXT NOT NULL DEFAULT 'final',
            factor TEXT NOT NULL DEFAULT '1.0',
            sort_order INTEGER NOT NULL DEFAULT 0,

            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),

            PRIMARY KEY (takeoff_id, item_code),
            FOREIGN KEY (takeoff_id) REFERENCES takeoffs(takeoff_id) ON DELETE CASCADE,
            FOREIGN KEY (item_code) REFERENCES items(internal_item_code)
        )
        """
    )

    # Additive migrations for takeoff_lines (older DBs)
    if not _has_column(conn, "takeoff_lines", "details_snapshot"):
        conn.execute("ALTER TABLE takeoff_lines ADD COLUMN details_snapshot TEXT NULL")
    if not _has_column(conn, "takeoff_lines", "notes"):
        conn.execute("ALTER TABLE takeoff_lines ADD COLUMN notes TEXT NULL")

    # Ensure TemplateLine v2 fields exist on snapshot lines too
    if not _has_column(conn, "takeoff_lines", "stage"):
        conn.execute("ALTER TABLE takeoff_lines ADD COLUMN stage TEXT NOT NULL DEFAULT 'final'")
    if not _has_column(conn, "takeoff_lines", "factor"):
        conn.execute("ALTER TABLE takeoff_lines ADD COLUMN factor TEXT NOT NULL DEFAULT '1.0'")
    if not _has_column(conn, "takeoff_lines", "sort_order"):
        conn.execute("ALTER TABLE takeoff_lines ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")

    # Backfill NULL stage on legacy DBs
    conn.execute("UPDATE takeoff_lines SET stage = 'final' WHERE stage IS NULL")

    # -------------------------
    # Takeoff versions (immutable)
    # -------------------------
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS takeoff_versions (
            version_id TEXT PRIMARY KEY,
            takeoff_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            notes TEXT NULL,

            -- Pin context for reproducible rendering
            project_code_snapshot TEXT NOT NULL DEFAULT '',
            template_code_snapshot TEXT NOT NULL DEFAULT '',

            -- Snapshotted financial context
            tax_rate_snapshot TEXT NOT NULL,
            valve_discount_snapshot TEXT NOT NULL DEFAULT '0.00',

            created_at TEXT NOT NULL DEFAULT (datetime('now')),

            FOREIGN KEY (takeoff_id) REFERENCES takeoffs(takeoff_id) ON DELETE CASCADE,
            UNIQUE (takeoff_id, version_number)
        )
        """
    )

    # Additive migrations for takeoff_versions (older DBs)
    if not _has_column(conn, "takeoff_versions", "tax_rate_snapshot"):
        conn.execute("ALTER TABLE takeoff_versions ADD COLUMN tax_rate_snapshot TEXT NOT NULL DEFAULT '0.07'")
    if not _has_column(conn, "takeoff_versions", "valve_discount_snapshot"):
        conn.execute(
            "ALTER TABLE takeoff_versions ADD COLUMN valve_discount_snapshot TEXT NOT NULL DEFAULT '0.00'"
        )
    if not _has_column(conn, "takeoff_versions", "project_code_snapshot"):
        conn.execute(
            "ALTER TABLE takeoff_versions ADD COLUMN project_code_snapshot TEXT NOT NULL DEFAULT ''"
        )
    if not _has_column(conn, "takeoff_versions", "template_code_snapshot"):
        conn.execute(
            "ALTER TABLE takeoff_versions ADD COLUMN template_code_snapshot TEXT NOT NULL DEFAULT ''"
        )

    # Enforce one takeoff per (project_code, template_code)
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_takeoffs_project_template
        ON takeoffs(project_code, template_code)
        """
    )    
    
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS takeoff_version_lines (
            version_id TEXT NOT NULL,
            item_code TEXT NOT NULL,
            qty TEXT NOT NULL,
            notes TEXT NULL,

            -- SNAPSHOT FIELDS (do not depend on live catalog later)
            description_snapshot TEXT NOT NULL,
            details_snapshot TEXT NULL,
            unit_price_snapshot TEXT NOT NULL,
            taxable_snapshot INTEGER NOT NULL,

            -- Ordering / costing modifiers
            stage TEXT NOT NULL DEFAULT 'final',
            factor TEXT NOT NULL DEFAULT '1.0',
            sort_order INTEGER NOT NULL DEFAULT 0,

            created_at TEXT NOT NULL DEFAULT (datetime('now')),

            PRIMARY KEY (version_id, item_code),
            FOREIGN KEY (version_id) REFERENCES takeoff_versions(version_id) ON DELETE CASCADE
        )
        """
    )

    # Additive migrations for takeoff_version_lines (older DBs)
    if not _has_column(conn, "takeoff_version_lines", "qty"):
        conn.execute("ALTER TABLE takeoff_version_lines ADD COLUMN qty TEXT NOT NULL DEFAULT '0'")
    if not _has_column(conn, "takeoff_version_lines", "notes"):
        conn.execute("ALTER TABLE takeoff_version_lines ADD COLUMN notes TEXT NULL")
    if not _has_column(conn, "takeoff_version_lines", "details_snapshot"):
        conn.execute("ALTER TABLE takeoff_version_lines ADD COLUMN details_snapshot TEXT NULL")
    if not _has_column(conn, "takeoff_version_lines", "created_at"):
        conn.execute(
            "ALTER TABLE takeoff_version_lines ADD COLUMN created_at TEXT NOT NULL DEFAULT (datetime('now'))"
        )
    if not _has_column(conn, "takeoff_version_lines", "stage"):
        conn.execute("ALTER TABLE takeoff_version_lines ADD COLUMN stage TEXT NOT NULL DEFAULT 'final'")
    if not _has_column(conn, "takeoff_version_lines", "factor"):
        conn.execute("ALTER TABLE takeoff_version_lines ADD COLUMN factor TEXT NOT NULL DEFAULT '1.0'")
    if not _has_column(conn, "takeoff_version_lines", "sort_order"):
        conn.execute("ALTER TABLE takeoff_version_lines ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")

    conn.commit()