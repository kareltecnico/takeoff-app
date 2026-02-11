from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from app.application.generate_takeoff_report_output import GenerateTakeoffReportOutput
from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine
from app.infrastructure.csv_takeoff_renderer import CsvTakeoffReportRenderer
from app.infrastructure.debug_takeoff_json_renderer import DebugJsonTakeoffReportRenderer
from app.infrastructure.pdf_takeoff_reportlab import ReportLabTakeoffPdfRenderer
from app.infrastructure.takeoff_json_loader import TakeoffJsonLoader
from app.reporting.renderers import TakeoffReportRenderer


#helper
def D(x: str) -> Decimal:
    return Decimal(x)

def _renderer_for(fmt: str) -> TakeoffReportRenderer:
    if fmt == "pdf":
        return ReportLabTakeoffPdfRenderer()
    if fmt == "json":
        return DebugJsonTakeoffReportRenderer()
    if fmt == "csv":
        return CsvTakeoffReportRenderer()
    raise SystemExit(f"Unknown format: {fmt!r}")


def _sample_takeoff() -> Takeoff:
    header = TakeoffHeader(
        project_name="TEST PROJECT",
        contractor_name="LENNAR",
        model_group_display="1331",
        stories=2,
        models=("1331",),
    )

    lines = (
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
            factor=Decimal("1"),
            sort_order=1,
        ),
    )

    return Takeoff(header=header, tax_rate=Decimal("0.07"), lines=lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="takeoff-app")
    sub = parser.add_subparsers(dest="cmd", required=True)

    render = sub.add_parser("render")
    render.add_argument(
        "--input",
        choices=["sample", "json"],
        default="sample",
        help="Input source: sample (built-in) or json (from file).",
    )
    render.add_argument(
        "--input-path",
        default=None,
        help="Path to JSON file (required when --input json).",
    )
    render.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
    render.add_argument("--out", required=True)

    args = parser.parse_args(argv)

    if args.cmd != "render":
        raise SystemExit(f"Unknown command: {args.cmd!r}")

    out = Path(args.out)
    renderer = _renderer_for(args.format)
    use_case = GenerateTakeoffReportOutput(renderer=renderer)

    if args.input == "json":
        if not args.input_path:
            raise SystemExit("--input-path is required when --input json is used")
        takeoff = TakeoffJsonLoader().load(Path(args.input_path))
    else:
        takeoff = _sample_takeoff()

    use_case(takeoff, out)
    print(f"{args.format.upper()} generated at: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())