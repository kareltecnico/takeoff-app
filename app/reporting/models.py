from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ReportLine:
    item_number: str
    description: str
    details: str | None
    unit_price: Decimal
    qty: Decimal
    factor: Decimal
    subtotal: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True)
class ReportSection:
    title: str  # "GROUND", "TOPOUT", "FINAL"
    lines: tuple[ReportLine, ...]
    subtotal: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True)
class ReportGrandTotals:
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    valve_discount: Decimal
    total_after_discount: Decimal


@dataclass(frozen=True)
class TakeoffReport:
    company_name: str
    created_at: datetime

    project_name: str
    contractor_name: str
    model_group_display: str
    stories: int
    models: tuple[str, ...]

    tax_rate: Decimal

    sections: tuple[ReportSection, ...]
    grand_totals: ReportGrandTotals
