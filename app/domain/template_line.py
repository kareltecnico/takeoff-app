from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.stage import Stage


@dataclass(frozen=True)
class TemplateLine:
    """
    A line inside a Template.

    This is *not* a takeoff snapshot line.
    It's the "blueprint" that will be expanded into a Takeoff snapshot.
    """

    template_code: str
    item_code: str
    qty: Decimal
    stage: Stage = Stage.FINAL
    factor: Decimal = Decimal("1.0")
    sort_order: int = 0
    notes: str | None = None