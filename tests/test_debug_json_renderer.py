from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from app.application.generate_takeoff_report_output import GenerateTakeoffReportOutput
from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine
from app.infrastructure.debug_takeoff_json_renderer import DebugJsonTakeoffReportRenderer


def test_debug_json_renderer_writes_report_json() -> None:
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
        )
    ]

    takeoff = Takeoff(header=header, tax_rate=Decimal("0.07"), lines=lines)

    with TemporaryDirectory() as td:
        out = Path(td) / "takeoff_report.json"
        use_case = GenerateTakeoffReportOutput(renderer=DebugJsonTakeoffReportRenderer())
        use_case(takeoff, out)

        assert out.exists()
        txt = out.read_text(encoding="utf-8")
        # Simple smoke assertions that confirm structure and key fields.
        assert "TEST PROJECT" in txt
        assert "GROUND" in txt
        assert "grand_totals" in txt
