from decimal import Decimal

from app.domain.stage import Stage
from app.domain.totals import TakeoffLineInput, calc_grand_totals, calc_stage_totals


def test_stage_totals_sums_lines_by_stage():
    lines = [
        TakeoffLineInput(
            stage=Stage.GROUND,
            price=Decimal("100"),
            qty=Decimal("1"),
            factor=Decimal("0.3"),
            taxable=False,
        ),
        TakeoffLineInput(
            stage=Stage.GROUND,
            price=Decimal("10"),
            qty=Decimal("2"),
            factor=Decimal("1"),
            taxable=True,
        ),
        TakeoffLineInput(
            stage=Stage.FINAL,
            price=Decimal("50"),
            qty=Decimal("1"),
            factor=Decimal("1"),
            taxable=True,
        ),
    ]

    ground = calc_stage_totals(lines, stage=Stage.GROUND)
    # Line1 subtotal = 100*1*0.3 = 30.00, no tax
    # Line2 subtotal = 10*2*1 = 20.00, tax=1.40
    assert ground.subtotal == Decimal("50.00")
    assert ground.tax == Decimal("1.40")
    assert ground.total == Decimal("51.40")

    final = calc_stage_totals(lines, stage=Stage.FINAL)
    assert final.subtotal == Decimal("50.00")
    assert final.tax == Decimal("3.50")
    assert final.total == Decimal("53.50")


def test_grand_totals_apply_valve_discount():
    lines = [
        TakeoffLineInput(
            stage=Stage.GROUND,
            price=Decimal("100"),
            qty=Decimal("1"),
            factor=Decimal("1"),
            taxable=True,
        )
    ]
    gt = calc_grand_totals(lines, valve_discount=Decimal("-112.99"))
    # subtotal=100.00 tax=7.00 total=107.00 after=-5.99
    assert gt.subtotal == Decimal("100.00")
    assert gt.tax == Decimal("7.00")
    assert gt.total == Decimal("107.00")
    assert gt.total_after_discount == Decimal("-5.99")
