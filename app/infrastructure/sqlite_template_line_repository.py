from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.application.repositories.template_line_repository import TemplateLineRepository
from app.domain.stage import Stage
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
        if line.factor <= Decimal("0"):
            raise InvalidInputError("TemplateLine.factor must be > 0")
        if line.sort_order < 0:
            raise InvalidInputError("TemplateLine.sort_order must be >= 0")
        if not isinstance(line.stage, Stage):
            raise InvalidInputError("TemplateLine.stage must be a Stage enum value")

        try:
            self.conn.execute(
                """
                INSERT INTO template_lines (
                    template_code,
                    item_code,
                    qty,
                    stage,
                    factor,
                    sort_order,
                    notes,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(template_code, item_code) DO UPDATE SET
                    qty=excluded.qty,
                    stage=excluded.stage,
                    factor=excluded.factor,
                    sort_order=excluded.sort_order,
                    notes=excluded.notes,
                    updated_at=datetime('now')
                """,
                (
                    line.template_code,
                    line.item_code,
                    str(line.qty),
                    line.stage.value,
                    str(line.factor),
                    int(line.sort_order),
                    line.notes,
                ),
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
            SELECT template_code, item_code, qty, stage, factor, sort_order, notes
            FROM template_lines
            WHERE template_code = ?
            ORDER BY sort_order, item_code
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
                    stage=Stage(str(r["stage"])),
                    factor=Decimal(str(r["factor"])),
                    sort_order=int(r["sort_order"]),
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