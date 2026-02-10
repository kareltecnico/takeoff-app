from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.application.generate_takeoff_pdf import GenerateTakeoffPdf
from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine
from app.infrastructure.pdf_takeoff_reportlab import ReportLabTakeoffPdfRenderer


def build_sample_takeoff() -> Takeoff:
    header = TakeoffHeader(
        project_name="TEST PROJECT",
        contractor_name="LENNAR",
        model_group_display="1331",
        stories=2,
        models=("1331",),
    )

    lines = [
        TakeoffLine(
            item=Item(
                code="WATER_HEATER_CONN",
                item_number="A100",
                description="Water heater connection",
                details="Sample line item",
                unit_price=Decimal("250.00"),
                taxable=True,
            ),
            stage=Stage.GROUND,
            qty=Decimal("1"),
            factor=Decimal("1.0"),
            sort_order=1,
        ),
        TakeoffLine(
            item=Item(
                code="TRIM_INSTALL",
                item_number="B200",
                description="Trim set install",
                details=None,
                unit_price=Decimal("120.00"),
                taxable=False,
            ),
            stage=Stage.FINAL,
            qty=Decimal("2"),
            factor=Decimal("1.0"),
            sort_order=2,
        ),
    ]

    return Takeoff(header=header, tax_rate=Decimal("0.07"), lines=lines)


def main() -> None:
    takeoff = build_sample_takeoff()

    output = Path("outputs/test_takeoff.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)

    use_case = GenerateTakeoffPdf(renderer=ReportLabTakeoffPdfRenderer())
    use_case(takeoff, output)
    print(f"PDF generated at: {output.resolve()}")


if __name__ == "__main__":
    main()