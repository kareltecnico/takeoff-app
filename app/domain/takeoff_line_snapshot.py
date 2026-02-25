from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


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
