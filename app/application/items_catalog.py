from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.application.repositories.item_repository import ItemRepository
from app.domain.item import Item


@dataclass(frozen=True)
class ItemsCatalog:
    repo: ItemRepository

    def add(
        self,
        *,
        code: str,
        description: str,
        unit_price: Decimal,
        taxable: bool,
        item_number: str | None = None,
        details: str | None = None,
        is_active: bool = True,
    ) -> None:
        code = code.strip()
        description = description.strip()

        if not code:
            raise InvalidInputError("--code cannot be empty")
        if not description:
            raise InvalidInputError("--description cannot be empty")
        if unit_price < Decimal("0"):
            raise InvalidInputError("--unit-price must be >= 0")

        self.repo.upsert(
            Item(
                code=code,
                item_number=item_number,
                description=description,
                details=details,
                unit_price=unit_price,
                taxable=taxable,
                is_active=is_active,
            )
        )

    def get(self, *, code: str) -> Item:
        return self.repo.get(code)

    def list(self, *, include_inactive: bool = False) -> tuple[Item, ...]:
        return self.repo.list(include_inactive=include_inactive)

    def update(
        self,
        *,
        code: str,
        description: str | None = None,
        unit_price: Decimal | None = None,
        taxable: bool | None = None,
        item_number: str | None = None,
        details: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        current = self.repo.get(code)

        new_item = Item(
            code=current.code,
            item_number=item_number if item_number is not None else current.item_number,
            description=description.strip() if description is not None else current.description,
            details=details if details is not None else current.details,
            unit_price=unit_price if unit_price is not None else current.unit_price,
            taxable=taxable if taxable is not None else current.taxable,
            is_active=is_active if is_active is not None else current.is_active,
        )

        if not new_item.description.strip():
            raise InvalidInputError("--description cannot be empty")
        if new_item.unit_price < Decimal("0"):
            raise InvalidInputError("--unit-price must be >= 0")

        self.repo.upsert(new_item)

    def delete(self, *, code: str) -> None:
        self.repo.delete(code)
