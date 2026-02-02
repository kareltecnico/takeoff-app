from decimal import Decimal

from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff_line import TakeoffLine


def test_takeoff_line_totals_respect_factor_and_tax():
    item = Item(
        code="KITCH_FAUCET_STD",
        item_number="L-123",
        description="Kitchen Faucet",
        details="Chrome",
        unit_price=Decimal("100"),
        taxable=True,
    )

    line = TakeoffLine(
        item=item,
        stage=Stage.FINAL,
        qty=Decimal("1"),
        factor=Decimal("0.4"),
        sort_order=10,
    )

    totals = line.totals()

    assert totals.subtotal == Decimal("40.00")
    assert totals.tax == Decimal("2.80")
    assert totals.total == Decimal("42.80")
