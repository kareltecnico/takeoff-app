from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.application.repositories.item_repository import ItemRepository
from app.domain.item import Item


def _b(value: bool) -> int:
    return 1 if value else 0


def _bool(value: object) -> bool:
    # SQLite returns ints (0/1), but be defensive for typing + safety.
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, (str, bytes, bytearray)):
        return int(value) != 0
    raise TypeError(f"Expected boolean-ish SQLite value, got {type(value).__name__}")


@dataclass(frozen=True)
class SqliteItemRepository(ItemRepository):
    conn: sqlite3.Connection

    def upsert(self, item: Item) -> None:
        if not item.code.strip():
            raise InvalidInputError("Item.code cannot be empty")

        self.conn.execute(
            """
            INSERT INTO items (
                internal_item_code,
                lennar_item_number,
                description1,
                description2,
                unit_price,
                default_taxable,
                is_active,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(internal_item_code) DO UPDATE SET
                lennar_item_number=excluded.lennar_item_number,
                description1=excluded.description1,
                description2=excluded.description2,
                unit_price=excluded.unit_price,
                default_taxable=excluded.default_taxable,
                is_active=excluded.is_active,
                updated_at=datetime('now')
            """,
            (
                item.code,
                item.item_number,
                item.description,
                item.details,
                str(item.unit_price),
                _b(item.taxable),
                _b(item.is_active),
            ),
        )
        self.conn.commit()

    def get(self, code: str) -> Item:
        row = self.conn.execute(
            """
            SELECT internal_item_code, lennar_item_number, description1, description2,
                   unit_price, default_taxable, is_active
            FROM items
            WHERE internal_item_code = ?
            """,
            (code,),
        ).fetchone()

        if row is None:
            raise InvalidInputError(f"Item not found: {code}")

        return Item(
            code=str(row["internal_item_code"]),
            item_number=row["lennar_item_number"],
            description=str(row["description1"]),
            details=row["description2"],
            unit_price=Decimal(str(row["unit_price"])),
            taxable=_bool(row["default_taxable"]),
            is_active=_bool(row["is_active"]),
        )

    def list(self, *, include_inactive: bool = False) -> tuple[Item, ...]:
        if include_inactive:
            rows = self.conn.execute(
                """
                SELECT internal_item_code, lennar_item_number, description1, description2,
                       unit_price, default_taxable, is_active
                FROM items
                ORDER BY internal_item_code
                """
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT internal_item_code, lennar_item_number, description1, description2,
                       unit_price, default_taxable, is_active
                FROM items
                WHERE is_active = 1
                ORDER BY internal_item_code
                """
            ).fetchall()

        out: list[Item] = []
        for row in rows:
            out.append(
                Item(
                    code=str(row["internal_item_code"]),
                    item_number=row["lennar_item_number"],
                    description=str(row["description1"]),
                    details=row["description2"],
                    unit_price=Decimal(str(row["unit_price"])),
                    taxable=_bool(row["default_taxable"]),
                    is_active=_bool(row["is_active"]),
                )
            )
        return tuple(out)

    def delete(self, code: str) -> None:
        cur = self.conn.execute(
            "DELETE FROM items WHERE internal_item_code = ?",
            (code,),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            raise InvalidInputError(f"Item not found: {code}")