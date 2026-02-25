from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TemplateLine:
    template_code: str
    item_code: str
    qty: Decimal
    notes: str | None = None
