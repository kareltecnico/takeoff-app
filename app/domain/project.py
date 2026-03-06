from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Project:
    code: str
    name: str
    contractor: str | None
    foreman: str | None
    is_active: bool = True
    valve_discount: Decimal = Decimal("0.00")