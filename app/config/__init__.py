from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AppConfig:
    company_name: str = "LEZA'S PLUMBING"
    default_tax_rate: Decimal = Decimal("0.07")
