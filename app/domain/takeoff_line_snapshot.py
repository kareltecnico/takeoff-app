from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.stage import Stage


@dataclass(frozen=True)
class TakeoffLineSnapshot:
    takeoff_id: str
    item_code: str
    qty: Decimal
    notes: str | None

    description_snapshot: str
    details_snapshot: str | None
    unit_price_snapshot: Decimal
    taxable_snapshot: bool

    # TemplateLine v2 fields (copied into snapshot at seed-time)
    stage: Stage | None = None
    factor: Decimal = Decimal("1.0")
    sort_order: int = 0
    line_id: str | None = None
    mapping_id: str | None = None
