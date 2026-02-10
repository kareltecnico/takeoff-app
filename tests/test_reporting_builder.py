from datetime import datetime
from decimal import Decimal

from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine
from app.reporting.builder import build_takeoff_report


def test_build_takeoff_report_contains_sections_and_totals() -> None:
    header = TakeoffHeader(
        project_name="P",
        contractor_name="C",
        model_group_display="1331",
        stories=2,
        models=["1331"],
    )

    lines = [
        TakeoffLine(
            item=Item(
                code="A",
                item_number="A100",
                description="Desc",
                details=None,
                unit_price=Decimal("100.00"),
                taxable=True,
            ),
            stage=Stage.GROUND,
            qty=Decimal("1"),
            factor=Decimal("1.0"),
            sort_order=1,
        )
    ]

    takeoff = Takeoff(header=header, tax_rate=Decimal("0.07"), lines=lines)
    report = build_takeoff_report(takeoff, created_at=datetime(2026, 1, 1, 0, 0, 0))

    assert report.project_name == "P"
    assert len(report.sections) == 3
    assert report.sections[0].title == "GROUND"
    assert len(report.sections[0].lines) == 1
    assert report.grand_totals.total_after_discount >= Decimal("0")
