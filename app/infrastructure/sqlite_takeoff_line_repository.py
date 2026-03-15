from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from app.application.repositories.takeoff_line_repository import TakeoffLineRepository
from app.application.errors import InvalidInputError
from app.domain.stage import Stage
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
                    stage,
                    factor,
                    sort_order,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
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
                        getattr(ln, "stage", None).value
                        if isinstance(getattr(ln, "stage", None), Stage)
                        else getattr(ln, "stage", None),
                        str(getattr(ln, "factor", Decimal("1.0"))),
                        int(getattr(ln, "sort_order", 0)),
                    )
                    for ln in lines
                ],
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def add_line(self, line: TakeoffLineSnapshot) -> None:
        if not str(line.takeoff_id).strip():
            raise InvalidInputError("takeoff_id cannot be empty")
        if not str(line.item_code).strip():
            raise InvalidInputError("item_code cannot be empty")
        if line.qty <= Decimal("0"):
            raise InvalidInputError("qty must be > 0")
        if line.factor <= Decimal("0"):
            raise InvalidInputError("factor must be > 0")
        if line.sort_order < 0:
            raise InvalidInputError("sort_order must be >= 0")

        takeoff_row = self.conn.execute(
            "SELECT is_locked FROM takeoffs WHERE takeoff_id = ?",
            (line.takeoff_id,),
        ).fetchone()
        if takeoff_row is None:
            raise InvalidInputError(f"Takeoff not found: {line.takeoff_id}")
        if bool(int(takeoff_row["is_locked"])):
            raise InvalidInputError(f"Takeoff is locked: {line.takeoff_id}")

        existing = self.conn.execute(
            """
            SELECT 1
            FROM takeoff_lines
            WHERE takeoff_id = ? AND item_code = ?
            """,
            (line.takeoff_id, line.item_code),
        ).fetchone()
        if existing is not None:
            raise InvalidInputError(
                f"Takeoff line already exists: takeoff_id={line.takeoff_id} item_code={line.item_code}"
            )

        self.conn.execute(
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
                stage,
                factor,
                sort_order,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                line.takeoff_id,
                line.item_code,
                str(line.qty),
                line.notes,
                line.description_snapshot,
                line.details_snapshot,
                str(line.unit_price_snapshot),
                _b(line.taxable_snapshot),
                line.stage.value if isinstance(line.stage, Stage) else str(line.stage or "final"),
                str(line.factor),
                int(line.sort_order),
            ),
        )
        self.conn.commit()
    
    def update_line(
        self,
        *,
        takeoff_id: str,
        item_code: str,
        qty: Decimal | None = None,
        stage: Stage | None = None,
        factor: Decimal | None = None,
        sort_order: int | None = None,
    ) -> None:
        if not str(takeoff_id).strip():
            raise InvalidInputError("takeoff_id cannot be empty")
        if not str(item_code).strip():
            raise InvalidInputError("item_code cannot be empty")

        takeoff_row = self.conn.execute(
            "SELECT is_locked FROM takeoffs WHERE takeoff_id = ?",
            (takeoff_id,),
        ).fetchone()
        if takeoff_row is None:
            raise InvalidInputError(f"Takeoff not found: {takeoff_id}")
        if bool(int(takeoff_row["is_locked"])):
            raise InvalidInputError(f"Takeoff is locked: {takeoff_id}")

        row = self.conn.execute(
            """
            SELECT qty, stage, factor, sort_order
            FROM takeoff_lines
            WHERE takeoff_id = ? AND item_code = ?
            """,
            (takeoff_id, item_code),
        ).fetchone()

        if row is None:
            raise InvalidInputError(
                f"Takeoff line not found: takeoff_id={takeoff_id} item_code={item_code}"
            )

        new_qty = qty if qty is not None else Decimal(str(row["qty"]))
        new_stage = stage if stage is not None else Stage(str(row["stage"] or "final"))
        new_factor = factor if factor is not None else Decimal(str(row["factor"] or "1.0"))
        new_sort_order = sort_order if sort_order is not None else int(row["sort_order"] or 0)

        if new_qty <= Decimal("0"):
            raise InvalidInputError("qty must be > 0")
        if new_factor <= Decimal("0"):
            raise InvalidInputError("factor must be > 0")
        if new_sort_order < 0:
            raise InvalidInputError("sort_order must be >= 0")

        self.conn.execute(
            """
            UPDATE takeoff_lines
            SET qty = ?,
                stage = ?,
                factor = ?,
                sort_order = ?,
                updated_at = datetime('now')
            WHERE takeoff_id = ? AND item_code = ?
            """,
            (
                str(new_qty),
                new_stage.value,
                str(new_factor),
                int(new_sort_order),
                takeoff_id,
                item_code,
            ),
        )
        self.conn.commit()    

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
                taxable_snapshot,
                stage,
                factor,
                sort_order
            FROM takeoff_lines
            WHERE takeoff_id = ?
            ORDER BY
                CASE COALESCE(stage, 'final')
                    WHEN 'ground' THEN 0
                    WHEN 'topout' THEN 1
                    WHEN 'final' THEN 2
                    ELSE 99
                END,
                sort_order,
                item_code
            """,
            (takeoff_id,),
        ).fetchall()

        out: list[TakeoffLineSnapshot] = []
        for r in rows:
            base_kwargs = dict(
                takeoff_id=str(r["takeoff_id"]),
                item_code=str(r["item_code"]),
                qty=Decimal(str(r["qty"])),
                notes=r["notes"],
                description_snapshot=str(r["description_snapshot"]),
                details_snapshot=r["details_snapshot"],
                unit_price_snapshot=Decimal(str(r["unit_price_snapshot"])),
                taxable_snapshot=_bool(r["taxable_snapshot"]),
            )
            extra_kwargs = dict(
                stage=Stage(str(r["stage"])) if r["stage"] is not None else None,
                factor=Decimal(str(r["factor"])) if r["factor"] is not None else Decimal("1.0"),
                sort_order=int(r["sort_order"]) if r["sort_order"] is not None else 0,
            )
            try:
                out.append(TakeoffLineSnapshot(**base_kwargs, **extra_kwargs))
            except TypeError:
                out.append(TakeoffLineSnapshot(**base_kwargs))

        return tuple(out)
    
    def delete_line(self, *, takeoff_id: str, item_code: str) -> None:
        if not str(takeoff_id).strip():
            raise InvalidInputError("takeoff_id cannot be empty")
        if not str(item_code).strip():
            raise InvalidInputError("item_code cannot be empty")

        takeoff_row = self.conn.execute(
            "SELECT is_locked FROM takeoffs WHERE takeoff_id = ?",
            (takeoff_id,),
        ).fetchone()
        if takeoff_row is None:
            raise InvalidInputError(f"Takeoff not found: {takeoff_id}")
        if bool(int(takeoff_row["is_locked"])):
            raise InvalidInputError(f"Takeoff is locked: {takeoff_id}")

        cur = self.conn.execute(
            """
            DELETE FROM takeoff_lines
            WHERE takeoff_id = ? AND item_code = ?
            """,
            (takeoff_id, item_code),
        )
        self.conn.commit()

        if cur.rowcount == 0:
            raise InvalidInputError(
                f"Takeoff line not found: takeoff_id={takeoff_id} item_code={item_code}"
            )