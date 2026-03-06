from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.totals import GrandTotals

__all__ = [
    "ReportGrandTotals",
    "ReportLine",
    "ReportSection",
    "TakeoffReport",
]

# Backwards-compatible public name: older modules import ReportGrandTotals from here.
ReportGrandTotals = GrandTotals

@dataclass(frozen=True)
class ReportLine:
    item_number: str
    description: str
    unit_price: Decimal
    qty: Decimal
    factor: Decimal
    subtotal: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True)
class ReportSection:
    """
    A logical section in the report (we map this to a Stage in the domain).
    """
    title: str
    lines: tuple[ReportLine, ...]
    subtotal: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True)
class TakeoffReport:
    company_name: str
    project_name: str
    contractor_name: str
    model_group_display: str
    models: tuple[str, ...]
    stories: int
    created_at: datetime
    tax_rate: Decimal
    sections: tuple[ReportSection, ...]
    grand_totals: ReportGrandTotals