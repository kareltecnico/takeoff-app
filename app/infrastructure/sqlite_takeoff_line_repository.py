from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from app.application.repositories.takeoff_line_repository import TakeoffLineRepository
from app.domain.takeoff_line_snapshot import TakeoffLineSnapshot


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
class SqliteTakeoffLineRepository(TakeoffLineRepository):
    conn: sqlite3.Connection

    def bulk_insert(self, lines: list[TakeoffLineSnapshot]) -> None:
        if not lines:
            return

        self.conn.execute("BEGIN")
        try:
            self.conn.executemany(
                """
                INSERT INTO takeoff_lines (
                    takeoff_id,
                    item_code,
                    qty,
                    notes,
                    description_snapshot,
                    details_snapshot,
                    unit_price_snapshot,
                    taxable_snapshot,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                [
                    (
                        ln.takeoff_id,
                        ln.item_code,
                        str(ln.qty),
                        ln.notes,
                        ln.description_snapshot,
                        ln.details_snapshot,
                        str(ln.unit_price_snapshot),
                        _b(ln.taxable_snapshot),
                    )
                    for ln in lines
                ],
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def list_for_takeoff(self, takeoff_id: str) -> tuple[TakeoffLineSnapshot, ...]:
        rows = self.conn.execute(
            """
            SELECT
                takeoff_id,
                item_code,
                qty,
                notes,
                description_snapshot,
                details_snapshot,
                unit_price_snapshot,
                taxable_snapshot
            FROM takeoff_lines
            WHERE takeoff_id = ?
            ORDER BY item_code
            """,
            (takeoff_id,),
        ).fetchall()

        out: list[TakeoffLineSnapshot] = []
        for r in rows:
            out.append(
                TakeoffLineSnapshot(
                    takeoff_id=str(r["takeoff_id"]),
                    item_code=str(r["item_code"]),
                    qty=Decimal(str(r["qty"])),
                    notes=r["notes"],
                    description_snapshot=str(r["description_snapshot"]),
                    details_snapshot=r["details_snapshot"],
                    unit_price_snapshot=Decimal(str(r["unit_price_snapshot"])),
                    taxable_snapshot=_bool(r["taxable_snapshot"]),
                )
            )
        return tuple(out)
