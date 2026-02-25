from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.domain.takeoff_record import TakeoffRecord


@dataclass(frozen=True)
class SqliteTakeoffRepository:
    conn: sqlite3.Connection

    def create(self, takeoff: TakeoffRecord) -> None:
        self.conn.execute("BEGIN")
        try:
            self.conn.execute(
                """
                INSERT INTO takeoffs (
                    takeoff_id, project_code, template_code, tax_rate, updated_at
                )
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (
                    takeoff.takeoff_id, 
                    takeoff.project_code, 
                    takeoff.template_code, 
                    str(takeoff.tax_rate)
                ),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get(self, takeoff_id: str) -> TakeoffRecord:
        row = self.conn.execute(
            """
            SELECT takeoff_id, project_code, template_code, tax_rate, created_at
            FROM takeoffs
            WHERE takeoff_id = ?
            """,
            (takeoff_id,),
        ).fetchone()

        if not row:
            raise InvalidInputError(f"Takeoff not found: {takeoff_id}")

        return TakeoffRecord(
            takeoff_id=str(row["takeoff_id"]),
            project_code=str(row["project_code"]),
            template_code=str(row["template_code"]),
            tax_rate=Decimal(str(row["tax_rate"])),
            created_at=str(row["created_at"]),
        )

    def list_for_project(self, project_code: str) -> tuple[TakeoffRecord, ...]:
        rows = self.conn.execute(
            """
            SELECT takeoff_id, project_code, template_code, tax_rate, created_at
            FROM takeoffs
            WHERE project_code = ?
            ORDER BY created_at DESC
            """,
            (project_code,),
        ).fetchall()

        out: list[TakeoffRecord] = []
        for r in rows:
            out.append(
                TakeoffRecord(
                    takeoff_id=str(r["takeoff_id"]),
                    project_code=str(r["project_code"]),
                    template_code=str(r["template_code"]),
                    tax_rate=Decimal(str(r["tax_rate"])),
                    created_at=str(r["created_at"]),
                )
            )
        return tuple(out)
