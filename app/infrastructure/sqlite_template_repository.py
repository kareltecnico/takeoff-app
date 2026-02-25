from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.application.errors import InvalidInputError
from app.application.repositories.template_repository import TemplateRepository
from app.domain.template import Template


def _b(value: bool) -> int:
    return 1 if value else 0


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, (str, bytes, bytearray)):
        return int(value) != 0
    raise TypeError(f"Expected boolean-ish SQLite value, got {type(value).__name__}")


@dataclass(frozen=True)
class SqliteTemplateRepository(TemplateRepository):
    conn: sqlite3.Connection

    def upsert(self, template: Template) -> None:
        if not template.code.strip():
            raise InvalidInputError("Template.code cannot be empty")
        if not template.name.strip():
            raise InvalidInputError("Template.name cannot be empty")
        if not template.category.strip():
            raise InvalidInputError("Template.category cannot be empty")

        self.conn.execute(
            """
            INSERT INTO templates (
                template_code, template_name, category, is_active, updated_at
            )
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(template_code) DO UPDATE SET
                template_name=excluded.template_name,
                category=excluded.category,
                is_active=excluded.is_active,
                updated_at=datetime('now')
            """,
            (template.code, template.name, template.category, _b(template.is_active)),
        )
        self.conn.commit()

    def get(self, code: str) -> Template:
        row = self.conn.execute(
            """
            SELECT template_code, template_name, category, is_active
            FROM templates
            WHERE template_code = ?
            """,
            (code,),
        ).fetchone()

        if row is None:
            raise InvalidInputError(f"Template not found: {code}")

        return Template(
            code=str(row["template_code"]),
            name=str(row["template_name"]),
            category=str(row["category"]),
            is_active=_bool(row["is_active"]),
        )

    def list(self, *, include_inactive: bool = False) -> tuple[Template, ...]:
        if include_inactive:
            rows = self.conn.execute(
                """
                SELECT template_code, template_name, category, is_active
                FROM templates
                ORDER BY template_code
                """
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT template_code, template_name, category, is_active
                FROM templates
                WHERE is_active = 1
                ORDER BY template_code
                """
            ).fetchall()

        out: list[Template] = []
        for r in rows:
            out.append(
                Template(
                    code=str(r["template_code"]),
                    name=str(r["template_name"]),
                    category=str(r["category"]),
                    is_active=_bool(r["is_active"]),
                )
            )
        return tuple(out)

    def delete(self, code: str) -> None:
        cur = self.conn.execute("DELETE FROM templates WHERE template_code = ?", (code,))
        self.conn.commit()
        if cur.rowcount == 0:
            raise InvalidInputError(f"Template not found: {code}")
