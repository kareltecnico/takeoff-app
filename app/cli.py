from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from app.application.generate_takeoff_pdf import GenerateTakeoffPdf
from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine
from app.infrastructure.csv_takeoff_renderer import CsvTakeoffReportRenderer
from app.infrastructure.debug_takeoff_json_renderer import DebugJsonTakeoffReportRenderer
from app.infrastructure.pdf_takeoff_reportlab import ReportLabTakeoffPdfRenderer
from app.reporting.renderers import TakeoffReportRenderer


def _sample_takeoff() -> Takeoff:
    header = TakeoffHeader(
        project_name="TEST PROJECT",
        contractor_name="LENNAR",
        model_group_display="1331",
        stories=2,
        models=("1331",),
    )

    lines: tuple[TakeoffLine, ...] = (
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
    )

    return Takeoff(header=header, tax_rate=Decimal("0.07"), lines=lines)


def _renderer_for(fmt: str) -> TakeoffReportRenderer:
    if fmt == "pdf":
        return ReportLabTakeoffPdfRenderer()
    if fmt == "json":
        return DebugJsonTakeoffReportRenderer()
    if fmt == "csv":
        return CsvTakeoffReportRenderer()
    raise ValueError(f"Unsupported format: {fmt}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="takeoff-app")
    sub = parser.add_subparsers(dest="cmd", required=True)

    render = sub.add_parser("render", help="Render a sample takeoff output")
    render.add_argument("--format", choices=("pdf", "json", "csv"), required=True)
    render.add_argument("--out", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.cmd == "render":
        takeoff = _sample_takeoff()
        renderer = _renderer_for(args.format)
        use_case = GenerateTakeoffPdf(renderer=renderer)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        use_case(takeoff, args.out)
        print(f"{args.format.upper()} generated at: {args.out.resolve()}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
