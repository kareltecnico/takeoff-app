from __future__ import annotations

from datetime import datetime

from app.domain.stage import Stage
from app.domain.takeoff import Takeoff
from app.reporting.models import ReportLine, ReportSection, TakeoffReport

__all__ = ["build_takeoff_report"]


def _stage_title(stage: Stage) -> str:
    # Stable, explicit section titles used by CSV/PDF/JSON.
    # Tests and customers rely on these exact strings.
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
    """
    Pure translation layer:
    Domain Takeoff -> Reporting TakeoffReport.

    - Sections map 1:1 to Stage (Ground/Topout/Final)
    - Lines are sorted by (sort_order, item_number, item_code) via Takeoff.lines_for_stage()
    - Totals are computed via domain calculation logic (TakeoffLine.totals / Takeoff.stage_totals / Takeoff.grand_totals)
    """
    created = created_at or datetime.now()

    stages: tuple[Stage, ...] = (Stage.GROUND, Stage.TOPOUT, Stage.FINAL)
    sections: list[ReportSection] = []

    for st in stages:
        report_lines: list[ReportLine] = []
        for ln in takeoff.lines_for_stage(st):
            t = ln.totals(tax_rate=takeoff.tax_rate)
            item_number = ln.item.item_number or ln.item.code
            report_lines.append(
                ReportLine(
                    item_number=item_number,
                    description=ln.item.description,
                    unit_price=ln.item.unit_price,
                    qty=ln.qty,
                    factor=ln.factor,
                    subtotal=t.subtotal,
                    tax=t.tax,
                    total=t.total,
                )
            )

        subtotal, tax, total = takeoff.stage_totals(st)

        sections.append(
            ReportSection(
                title=_stage_title(st),
                lines=tuple(report_lines),
                subtotal=subtotal,
                tax=tax,
                total=total,
            )
        )

    return TakeoffReport(
        company_name=company_name,
        project_name=takeoff.header.project_name,
        contractor_name=takeoff.header.contractor_name,
        model_group_display=takeoff.header.model_group_display,
        models=takeoff.header.models,
        stories=takeoff.header.stories,
        created_at=created,
        tax_rate=takeoff.tax_rate,
        sections=tuple(sections),
        grand_totals=takeoff.grand_totals(),
    )