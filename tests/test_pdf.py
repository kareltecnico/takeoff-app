from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine
from app.infrastructure.pdf_takeoff_reportlab import render_takeoff_pdf
from app.reporting.builder import build_takeoff_report


def test_pdf_is_generated_and_looks_like_pdf_header() -> None:
    header = TakeoffHeader(
        project_name="ABESS",
        contractor_name="LENNAR",
        model_group_display="P001-P002",
        models=("P001", "P002"),
        stories=1,
    )

    lines = (
        TakeoffLine(
            item=Item(
                code="MAT_PER_FIXTURE",
                item_number="1",
                description="MAT'L PER FIXTURE-1 STORY",
                details=None,
                unit_price=Decimal("100"),
                taxable=False,
            ),
            stage=Stage.GROUND,
            qty=Decimal("8"),
            factor=Decimal("0.3"),
            sort_order=1,
        ),
        TakeoffLine(
            item=Item(
                code="KITCH_FAUCET",
                item_number="10",
                description="FAUCET,KITCH,METHOD,CHROME",
                details=None,
                unit_price=Decimal("50"),
                taxable=True,
            ),
            stage=Stage.FINAL,
            qty=Decimal("1"),
            factor=Decimal("1"),
            sort_order=1,
        ),
    )

    takeoff = Takeoff(header=header, lines=lines)
    report = build_takeoff_report(takeoff, created_at=datetime(2026, 1, 1, 0, 0, 0))

    with TemporaryDirectory() as td:
        out = Path(td) / "ABESS (P001-P002).pdf"
        render_takeoff_pdf(report, out)

        data = out.read_bytes()
        assert data.startswith(b"%PDF")
        assert out.stat().st_size > 1_000