from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.domain.stage import Stage
from app.domain.takeoff import Takeoff
from app.reporting.models import (
    ReportGrandTotals,
    ReportLine,
    ReportSection,
    TakeoffReport,
)


def _stage_title(stage: Stage) -> str:
    return {
        Stage.GROUND: "GROUND",
        Stage.TOPOUT: "TOPOUT",
        Stage.FINAL: "FINAL",
    }[stage]


def build_takeoff_report(
    takeoff: Takeoff,
    *,
    company_name: str = "LEZA'S PLUMBING",
    created_at: datetime | None = None,
) -> TakeoffReport:
    """Build a report DTO from the domain Takeoff (no rendering, just mapping)."""
    created_at = created_at or datetime.now()
    header = takeoff.header

    sections: list[ReportSection] = []

    for stage in (Stage.GROUND, Stage.TOPOUT, Stage.FINAL):
        stage_lines = list(takeoff.lines_for_stage(stage))

        report_lines: list[ReportLine] = []
        for ln in stage_lines:
            t = ln.totals(tax_rate=takeoff.tax_rate)

            report_lines.append(
                ReportLine(
                    item_number=ln.item.item_number or "",
                    description=ln.item.description,
                    details=ln.item.details,
                    unit_price=ln.item.unit_price,
                    qty=ln.qty,
                    factor=ln.factor,
                    subtotal=t.subtotal,
                    tax=t.tax,
                    total=t.total,
                )
            )

        sub, tax, total = takeoff.stage_totals(stage)

        sections.append(
            ReportSection(
                title=_stage_title(stage),
                lines=tuple(report_lines),
                subtotal=sub,
                tax=tax,
                total=total,
            )
        )

    gt = takeoff.grand_totals()

    # Option A (Reports): never allow negative totals in the final displayed report.
    ZERO = Decimal("0.00")
    total_after_discount = max(ZERO, gt.total_after_discount)

    grand = ReportGrandTotals(
        subtotal=gt.subtotal,
        tax=gt.tax,
        total=gt.total,
        valve_discount=gt.valve_discount,
        total_after_discount=total_after_discount,
    )

    return TakeoffReport(
        company_name=company_name,
        created_at=created_at,
        project_name=header.project_name,
        contractor_name=header.contractor_name,
        model_group_display=header.model_group_display,
        stories=header.stories,
        models=tuple(header.models),
        tax_rate=takeoff.tax_rate,
        sections=tuple(sections),
        grand_totals=grand,
    )