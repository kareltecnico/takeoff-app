from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.stage import Stage
from app.domain.totals import TakeoffLineInput, calc_grand_totals


@dataclass(frozen=True)
class ProjectTakeoffSummary:
    takeoff_id: str
    project_code: str
    template_code: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    valve_discount: Decimal
    total_after_discount: Decimal


@dataclass(frozen=True)
class ProjectSummary:
    project_code: str
    takeoff_count: int
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    valve_discount: Decimal
    total_after_discount: Decimal
    takeoffs: tuple[ProjectTakeoffSummary, ...]


class SummarizeProject:
    """
    Application use case.

    Produces a financial summary across all takeoffs for a given project.
    """

    def __init__(self, *, takeoff_repo, takeoff_line_repo) -> None:
        self._takeoff_repo = takeoff_repo
        self._takeoff_line_repo = takeoff_line_repo

    def __call__(self, *, project_code: str) -> ProjectSummary:
        takeoffs = self._takeoff_repo.list_for_project(project_code=project_code)

        summaries: list[ProjectTakeoffSummary] = []

        subtotal = Decimal("0")
        tax = Decimal("0")
        total = Decimal("0")
        valve_discount = Decimal("0")
        total_after_discount = Decimal("0")

        for t in takeoffs:
            lines = list(self._takeoff_line_repo.list_for_takeoff(takeoff_id=t.takeoff_id))

            inputs: list[TakeoffLineInput] = []
            for ln in lines:
                stage = getattr(ln, "stage", None) or Stage.FINAL
                factor = getattr(ln, "factor", None) or Decimal("1.0")

                inputs.append(
                    TakeoffLineInput(
                        stage=stage,
                        price=ln.unit_price_snapshot,
                        qty=ln.qty,
                        factor=factor,
                        taxable=ln.taxable_snapshot,
                    )
                )

            gt = calc_grand_totals(
                inputs,
                valve_discount=t.valve_discount,
                tax_rate=t.tax_rate,
            )

            summaries.append(
                ProjectTakeoffSummary(
                    takeoff_id=t.takeoff_id,
                    project_code=t.project_code,
                    template_code=t.template_code,
                    subtotal=gt.subtotal,
                    tax=gt.tax,
                    total=gt.total,
                    valve_discount=gt.valve_discount,
                    total_after_discount=gt.total_after_discount,
                )
            )

            subtotal += gt.subtotal
            tax += gt.tax
            total += gt.total
            valve_discount += gt.valve_discount
            total_after_discount += gt.total_after_discount

        return ProjectSummary(
            project_code=project_code,
            takeoff_count=len(summaries),
            subtotal=subtotal,
            tax=tax,
            total=total,
            valve_discount=valve_discount,
            total_after_discount=total_after_discount,
            takeoffs=tuple(summaries),
        )