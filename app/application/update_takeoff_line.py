from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.domain.stage import Stage


@dataclass(frozen=True)
class UpdateTakeoffLine:
    repo: object

    def __call__(
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

        if qty is None and factor is None and stage is None and sort_order is None:
            raise InvalidInputError(
                "At least one of qty, stage, factor, sort_order must be provided"
            )

        self.repo.update_line(
            takeoff_id=takeoff_id,
            item_code=item_code,
            qty=qty,
            stage=stage,
            factor=factor,
            sort_order=sort_order,
        )
