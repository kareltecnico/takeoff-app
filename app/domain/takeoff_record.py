from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TakeoffRecord:
    takeoff_id: str
    project_code: str
    template_code: str
    tax_rate: Decimal
    model_display: str | None = None
    valve_discount: Decimal = Decimal("0.00")
    is_locked: bool = False
    created_at: str = ""
