from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.item import Item
from app.domain.money import LineTotals, calc_line_totals
from app.domain.stage import Stage


@dataclass(frozen=True)
class TakeoffLine:
    """
    One line inside a Take-Off (per stage).
    """
    item: Item
    stage: Stage
    qty: Decimal
    factor: Decimal
    sort_order: int

    def totals(
        self,
        *,
        tax_rate: Decimal = Decimal("0.07"),
    ) -> LineTotals:
        return calc_line_totals(
            price=self.item.unit_price,
            qty=self.qty,
            factor=self.factor,
            taxable=self.item.taxable,
            tax_rate=tax_rate,
        )
