from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.application.errors import InvalidInputError
from app.application.repositories.item_repository import ItemRepository
from app.domain.item import Item


def _as_str(value: object, *, field: str) -> str:
    if isinstance(value, str):
        return value
    raise ValueError(f"Field {field!r} must be a string, got {type(value).__name__}")


def _as_opt_str(value: object | None, *, field: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ValueError(f"Field {field!r} must be a string or null, got {type(value).__name__}")


def _as_bool(value: object, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"Field {field!r} must be a bool, got {type(value).__name__}")


def _as_decimal(value: object, *, field: str) -> Decimal:
    # Stored as string in JSON, but be robust.
    if isinstance(value, (int, float, str, Decimal)):
        return Decimal(str(value))
    raise ValueError(f"Field {field!r} must be numeric/string, got {type(value).__name__}")


def _item_to_dict(it: Item) -> dict[str, object]:
    return {
        "code": it.code,
        "item_number": it.item_number,
        "description": it.description,
        "details": it.details,
        "unit_price": str(it.unit_price),
        "taxable": it.taxable,
        "is_active": it.is_active,
    }


def _item_from_dict(d: dict[str, object]) -> Item:
    return Item(
        code=_as_str(d.get("code"), field="code"),
        item_number=_as_opt_str(d.get("item_number"), field="item_number"),
        description=_as_str(d.get("description"), field="description"),
        details=_as_opt_str(d.get("details"), field="details"),
        unit_price=_as_decimal(d.get("unit_price"), field="unit_price"),
        taxable=_as_bool(d.get("taxable"), field="taxable"),
        is_active=_as_bool(d.get("is_active", True), field="is_active"),
    )


@dataclass(frozen=True)
class FileItemRepository(ItemRepository):
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_all({})

    def _read_all(self) -> dict[str, Item]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))

        if not isinstance(raw, list):
            raise ValueError("Items catalog JSON must be a list")

        items: dict[str, Item] = {}
        for row in raw:
            if not isinstance(row, dict):
                raise ValueError("Items catalog entries must be objects")

            # json gives dict[str, object] effectively
            row_typed: dict[str, object] = dict(row)
            it = _item_from_dict(row_typed)
            items[it.code] = it

        return items

    def _write_all(self, items: dict[str, Item]) -> None:
        payload: list[dict[str, object]] = [_item_to_dict(it) for it in items.values()]
        payload.sort(key=lambda x: str(x["code"]))  # key must be orderable (str)

        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def upsert(self, item: Item) -> None:
        if not item.code.strip():
            raise InvalidInputError("Item.code cannot be empty")
        items = self._read_all()
        items[item.code] = item
        self._write_all(items)

    def get(self, code: str) -> Item:
        items = self._read_all()
        try:
            return items[code]
        except KeyError as e:
            raise InvalidInputError(f"Item not found: {code}") from e

    def list(self, *, include_inactive: bool = False) -> tuple[Item, ...]:
        items = self._read_all()
        vals = list(items.values())
        if not include_inactive:
            vals = [it for it in vals if it.is_active]
        vals.sort(key=lambda it: it.code)
        return tuple(vals)

    def delete(self, code: str) -> None:
        items = self._read_all()
        if code not in items:
            raise InvalidInputError(f"Item not found: {code}")
        del items[code]
        self._write_all(items)