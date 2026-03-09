from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff_line_snapshot import TakeoffLineSnapshot


@dataclass(frozen=True)
class AddTakeoffLine:
    repo: object

    def __call__(
        self,
        *,
        takeoff_id: str,
        item: Item,
        qty: Decimal,
        stage: Stage = Stage.FINAL,
        factor: Decimal = Decimal("1.0"),
        sort_order: int = 0,
        notes: str | None = None,
    ) -> None:
        if not str(takeoff_id).strip():
            raise InvalidInputError("takeoff_id cannot be empty")
        if qty <= Decimal("0"):
            raise InvalidInputError("qty must be > 0")
        if factor <= Decimal("0"):
            raise InvalidInputError("factor must be > 0")
        if sort_order < 0:
            raise InvalidInputError("sort_order must be >= 0")

        self.repo.add_line(
            TakeoffLineSnapshot(
                takeoff_id=takeoff_id,
                item_code=item.code,
                qty=qty,
                notes=notes,
                description_snapshot=item.description,
                details_snapshot=item.details,
                unit_price_snapshot=item.unit_price,
                taxable_snapshot=item.taxable,
                stage=stage,
                factor=factor,
                sort_order=sort_order,
            )
        )
