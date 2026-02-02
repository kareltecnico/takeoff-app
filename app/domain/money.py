from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

TWOPLACES = Decimal("0.01")


def q2(value: Decimal) -> Decimal:
    """Quantize to 2 decimals using normal accounting rounding."""
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LineTotals:
    subtotal: Decimal   # pre-tax
    tax: Decimal
    total: Decimal      # subtotal + tax


def calc_line_totals(
    *,
    price: Decimal,
    qty: Decimal,
    factor: Decimal,
    taxable: bool,
    tax_rate: Decimal = Decimal("0.07"),
) -> LineTotals:
    """
    Business rule:
      subtotal = price * qty * factor
      tax = subtotal * tax_rate if taxable else 0
      total = subtotal + tax

    All values returned rounded to 2 decimals.
    """
    subtotal = q2(price * qty * factor)
    tax = q2(subtotal * tax_rate) if taxable else Decimal("0.00")
    total = q2(subtotal + tax)
    return LineTotals(subtotal=subtotal, tax=tax, total=total)