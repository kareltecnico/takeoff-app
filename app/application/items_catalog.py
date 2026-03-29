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
        category: str | None = None,
    ) -> None:
        code = code.strip()
        description = description.strip()

        if not code:
            raise InvalidInputError("--code cannot be empty")
        if not description:
            raise InvalidInputError("--description cannot be empty")
        if unit_price < Decimal("0"):
            raise InvalidInputError("--unit-price must be >= 0")

        try:
            self.repo.get(code)
        except InvalidInputError:
            pass
        else:
            raise InvalidInputError(f"Item already exists: {code}")

        self.repo.upsert(
            Item(
                code=code,
                item_number=item_number,
                description=description,
                details=details,
                unit_price=unit_price,
                taxable=taxable,
                is_active=is_active,
                category=category,
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
        clear_item_number: bool = False,
        clear_details: bool = False,
        is_active: bool | None = None,
        category: str | None = None,
    ) -> None:
        if clear_item_number and item_number is not None:
            raise InvalidInputError("Use either --item-number or --clear-item-number, not both")
        if clear_details and details is not None:
            raise InvalidInputError("Use either --details or --clear-details, not both")
        if (
            description is None
            and unit_price is None
            and taxable is None
            and item_number is None
            and details is None
            and not clear_item_number
            and not clear_details
            and is_active is None
            and category is None
        ):
            raise InvalidInputError("No item changes were provided")

        current = self.repo.get(code)

        new_item = Item(
            code=current.code,
            item_number=(
                None
                if clear_item_number
                else item_number if item_number is not None else current.item_number
            ),
            description=description.strip() if description is not None else current.description,
            details=None if clear_details else details if details is not None else current.details,
            unit_price=unit_price if unit_price is not None else current.unit_price,
            taxable=taxable if taxable is not None else current.taxable,
            is_active=is_active if is_active is not None else current.is_active,
            category=category if category is not None else current.category,
        )

        if not new_item.description.strip():
            raise InvalidInputError("--description cannot be empty")
        if new_item.unit_price < Decimal("0"):
            raise InvalidInputError("--unit-price must be >= 0")

        self.repo.upsert(new_item)

    def delete(self, *, code: str) -> None:
        self.repo.delete(code)
