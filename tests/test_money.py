from decimal import Decimal

from app.domain.money import calc_line_totals


def test_non_taxable_line_has_zero_tax():
    t = calc_line_totals(price=Decimal("100"), qty=Decimal("2"), factor=Decimal("0.3"), taxable=False)
    assert t.subtotal == Decimal("60.00")
    assert t.tax == Decimal("0.00")
    assert t.total == Decimal("60.00")


def test_taxable_line_applies_7_percent_tax():
    t = calc_line_totals(price=Decimal("100"), qty=Decimal("2"), factor=Decimal("0.3"), taxable=True)
    assert t.subtotal == Decimal("60.00")
    assert t.tax == Decimal("4.20")      # 60.00 * 0.07
    assert t.total == Decimal("64.20")


def test_rounding_half_up():
    # 0.05 * 0.07 = 0.0035 => rounds to 0.00 with 2 decimals,
    # but ensure consistent accounting rounding behavior in subtotal first.
    t = calc_line_totals(price=Decimal("0.05"), qty=Decimal("1"), factor=Decimal("1"), taxable=True)
    assert t.subtotal == Decimal("0.05")
    assert t.tax == Decimal("0.00")
    assert t.total == Decimal("0.05")