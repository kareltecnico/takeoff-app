from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.application.repositories.template_line_repository import TemplateLineRepository
from app.domain.template_line import TemplateLine


@dataclass(frozen=True)
class SqliteTemplateLineRepository(TemplateLineRepository):
    conn: sqlite3.Connection

    def upsert(self, line: TemplateLine) -> None:
        if not line.template_code.strip():
            raise InvalidInputError("TemplateLine.template_code cannot be empty")
        if not line.item_code.strip():
            raise InvalidInputError("TemplateLine.item_code cannot be empty")
        if line.qty <= Decimal("0"):
            raise InvalidInputError("TemplateLine.qty must be > 0")

        try:
            self.conn.execute(
                """
                INSERT INTO template_lines (
                    template_code, item_code, qty, notes, updated_at
                )
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(template_code, item_code) DO UPDATE SET
                    qty=excluded.qty,
                    notes=excluded.notes,
                    updated_at=datetime('now')
                """,
                (line.template_code, line.item_code, str(line.qty), line.notes),
            )
        except sqlite3.IntegrityError as e:
            raise InvalidInputError(
                
                    "TemplateLine FK constraint failed "
                    f"(template={line.template_code!r}, item={line.item_code!r}). "
                    "Ensure the template and item exist before adding lines."
                
            ) from e   
        self.conn.commit()

    def list_for_template(self, template_code: str) -> tuple[TemplateLine, ...]:
        rows = self.conn.execute(
            """
            SELECT template_code, item_code, qty, notes
            FROM template_lines
            WHERE template_code = ?
            ORDER BY item_code
            """,
            (template_code,),
        ).fetchall()

        out: list[TemplateLine] = []
        for r in rows:
            out.append(
                TemplateLine(
                    template_code=str(r["template_code"]),
                    item_code=str(r["item_code"]),
                    qty=Decimal(str(r["qty"])),
                    notes=r["notes"],
                )
            )
        return tuple(out)

    def delete(self, template_code: str, item_code: str) -> None:
        cur = self.conn.execute(
            "DELETE FROM template_lines WHERE template_code = ? AND item_code = ?",
            (template_code, item_code),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            raise InvalidInputError(f"Template line not found: {template_code} / {item_code}")
