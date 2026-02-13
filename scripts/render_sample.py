from __future__ import annotations

import argparse
from pathlib import Path

from app.application.generate_takeoff_report_output import GenerateTakeoffReportOutput
from app.config import AppConfig
from app.infrastructure.csv_takeoff_renderer import CsvTakeoffReportRenderer
from app.infrastructure.debug_takeoff_json_renderer import DebugJsonTakeoffReportRenderer
from app.infrastructure.pdf_takeoff_reportlab import ReportLabTakeoffPdfRenderer
from scripts._sample_takeoff import build_sample_takeoff


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sample Take-Off output")
    parser.add_argument(
        "--format",
        choices=("pdf", "json", "csv"),
        default="pdf",
        help="Output format",
    )
    args = parser.parse_args()

    takeoff = build_sample_takeoff()

    if args.format == "pdf":
        renderer = ReportLabTakeoffPdfRenderer()
        output = Path("outputs/test_takeoff.pdf")

    elif args.format == "json":
        renderer = DebugJsonTakeoffReportRenderer()
        output = Path("outputs/test_takeoff_report.json")

    else:  # csv
        renderer = CsvTakeoffReportRenderer()
        output = Path("outputs/test_takeoff_report.csv")

    output.parent.mkdir(parents=True, exist_ok=True)

    use_case = GenerateTakeoffReportOutput(renderer=renderer, config=AppConfig())
    use_case(takeoff, output)

    print(f"{args.format.upper()} generated at: {output.resolve()}")


if __name__ == "__main__":
    main()
