from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TakeoffRecord:
    takeoff_id: str
    project_code: str
    template_code: str
    tax_rate: Decimal
    created_at: str
