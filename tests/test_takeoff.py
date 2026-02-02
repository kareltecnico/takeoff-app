from decimal import Decimal

from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine


def _item(code: str, price: str, taxable: bool) -> Item:
    return Item(
        code=code,
        item_number=None,
        description=code,
        details=None,
        unit_price=Decimal(price),
        taxable=taxable,
    )


def test_takeoff_lines_for_stage_sorted_by_sort_order():
    header = TakeoffHeader(
        project_name="ABESS",
        contractor_name="LENNAR",
        model_group_display="P001-P002",
        models=("P001", "P002"),
        stories=1,
    )

    ln1 = TakeoffLine(
        item=_item("A", "10", True),
        stage=Stage.GROUND,
        qty=Decimal("1"),
        factor=Decimal("1"),
        sort_order=20,
    )
    ln2 = TakeoffLine(
        item=_item("B", "10", True),
        stage=Stage.GROUND,
        qty=Decimal("1"),
        factor=Decimal("1"),
        sort_order=10,
    )

    t = Takeoff(header=header, lines=(ln1, ln2))
    ordered = t.lines_for_stage(Stage.GROUND)
    assert [ln.item.code for ln in ordered] == ["B", "A"]


def test_takeoff_stage_totals_and_grand_totals():
    header = TakeoffHeader(
        project_name="ABESS",
        contractor_name="LENNAR",
        model_group_display="P001",
        models=("P001",),
        stories=1,
    )

    # Ground: non-taxable split line => 100 * 1 * 0.3 = 30.00 tax 0.00
    ground_line = TakeoffLine(
        item=_item("MAT_PER_FIXTURE", "100", False),
        stage=Stage.GROUND,
        qty=Decimal("1"),
        factor=Decimal("0.3"),
        sort_order=1,
    )

    # Final: taxable material => 50 * 2 * 1 = 100.00 tax 7.00
    final_line = TakeoffLine(
        item=_item("KITCH_FAUCET", "50", True),
        stage=Stage.FINAL,
        qty=Decimal("2"),
        factor=Decimal("1"),
        sort_order=1,
    )

    takeoff = Takeoff(
        header=header,
        lines=(ground_line, final_line),
        valve_discount=Decimal("-112.99"),
        tax_rate=Decimal("0.07"),
    )

    g_sub, g_tax, g_total = takeoff.stage_totals(Stage.GROUND)
    assert g_sub == Decimal("30.00")
    assert g_tax == Decimal("0.00")
    assert g_total == Decimal("30.00")

    f_sub, f_tax, f_total = takeoff.stage_totals(Stage.FINAL)
    assert f_sub == Decimal("100.00")
    assert f_tax == Decimal("7.00")
    assert f_total == Decimal("107.00")

    gt = takeoff.grand_totals()
    assert gt.subtotal == Decimal("130.00")  # 30 + 100
    assert gt.tax == Decimal("7.00")
    assert gt.total == Decimal("137.00")
    assert gt.total_after_discount == Decimal("24.01")  # 137 - 112.99
