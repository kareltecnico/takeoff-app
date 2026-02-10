from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from app.reporting.models import TakeoffReport
from app.reporting.renderers import TakeoffReportRenderer


class _RowWriter(Protocol):
    def writerow(self, row: list[str]) -> object: ...


def _money(x: Decimal) -> str:
    return f"{x:.2f}"


def _write_report_lines(w: _RowWriter, report: TakeoffReport) -> None:
    # Header
    w.writerow(["company_name", report.company_name])
    w.writerow(["project_name", report.project_name])
    w.writerow(["contractor_name", report.contractor_name])
    w.writerow(["model_group_display", report.model_group_display])
    w.writerow(["stories", str(report.stories)])
    w.writerow(["models", ",".join(report.models)])
    w.writerow(["created_at", report.created_at.strftime("%Y-%m-%d %H:%M")])
    w.writerow(["tax_rate", str(report.tax_rate)])
    w.writerow([])

    # Detail lines
    w.writerow(
        [
            "section",
            "item_number",
            "description",
            "unit_price",
            "qty",
            "factor",
            "subtotal",
            "tax",
            "total",
        ]
    )

    for section in report.sections:
        for ln in section.lines:
            w.writerow(
                [
                    section.title,
                    ln.item_number,
                    ln.description,
                    _money(ln.unit_price),
                    str(ln.qty),
                    str(ln.factor),
                    _money(ln.subtotal),
                    _money(ln.tax),
                    _money(ln.total),
                ]
            )

    w.writerow([])

    # Section totals
    w.writerow(["section", "subtotal", "tax", "total"])
    for section in report.sections:
        w.writerow(
            [
                section.title,
                _money(section.subtotal),
                _money(section.tax),
                _money(section.total),
            ]
        )

    w.writerow([])

    # Grand totals
    gt = report.grand_totals
    w.writerow(["grand_subtotal", _money(gt.subtotal)])
    w.writerow(["grand_tax", _money(gt.tax)])
    w.writerow(["grand_total", _money(gt.total)])
    w.writerow(["valve_discount", _money(gt.valve_discount)])
    w.writerow(["total_after_discount", _money(gt.total_after_discount)])


@dataclass(frozen=True)
class CsvTakeoffReportRenderer(TakeoffReportRenderer):
    """
    Renders a TakeoffReport as CSV.

    Output is a "report style" CSV:
      - Key/value header lines
      - Detail lines table
      - Section totals table
      - Grand totals key/value lines
    """

    def render(self, report: TakeoffReport, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            _write_report_lines(w, report)

        return output_path