from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.stage import Stage
from app.domain.totals import TakeoffLineInput, calc_grand_totals, calc_stage_totals


@dataclass(frozen=True)
class StageInvoiceSummary:
    stage: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True)
class TakeoffInvoiceSummary:
    takeoff_id: str
    project_code: str
    template_code: str
    ground: StageInvoiceSummary
    topout: StageInvoiceSummary
    final: StageInvoiceSummary
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    valve_discount: Decimal
    total_after_discount: Decimal


@dataclass(frozen=True)
class ProjectInvoiceSummary:
    project_code: str
    takeoff_count: int
    ground_subtotal: Decimal
    ground_tax: Decimal
    ground_total: Decimal
    topout_subtotal: Decimal
    topout_tax: Decimal
    topout_total: Decimal
    final_subtotal: Decimal
    final_tax: Decimal
    final_total: Decimal
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    valve_discount: Decimal
    total_after_discount: Decimal
    takeoffs: tuple[TakeoffInvoiceSummary, ...]


class GenerateProjectInvoice:
    def __init__(self, *, takeoff_repo, takeoff_line_repo) -> None:
        self._takeoff_repo = takeoff_repo
        self._takeoff_line_repo = takeoff_line_repo

    def __call__(self, *, project_code: str) -> ProjectInvoiceSummary:
        takeoffs = self._takeoff_repo.list_for_project(project_code=project_code)

        out: list[TakeoffInvoiceSummary] = []

        ground_subtotal = Decimal("0")
        ground_tax = Decimal("0")
        ground_total = Decimal("0")

        topout_subtotal = Decimal("0")
        topout_tax = Decimal("0")
        topout_total = Decimal("0")

        final_subtotal = Decimal("0")
        final_tax = Decimal("0")
        final_total = Decimal("0")

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

            ground = calc_stage_totals(inputs, stage=Stage.GROUND, tax_rate=t.tax_rate)
            topout = calc_stage_totals(inputs, stage=Stage.TOPOUT, tax_rate=t.tax_rate)
            final = calc_stage_totals(inputs, stage=Stage.FINAL, tax_rate=t.tax_rate)
            grand = calc_grand_totals(
                inputs,
                valve_discount=t.valve_discount,
                tax_rate=t.tax_rate,
            )

            out.append(
                TakeoffInvoiceSummary(
                    takeoff_id=t.takeoff_id,
                    project_code=t.project_code,
                    template_code=t.template_code,
                    ground=StageInvoiceSummary(
                        stage="ground",
                        subtotal=ground.subtotal,
                        tax=ground.tax,
                        total=ground.total,
                    ),
                    topout=StageInvoiceSummary(
                        stage="topout",
                        subtotal=topout.subtotal,
                        tax=topout.tax,
                        total=topout.total,
                    ),
                    final=StageInvoiceSummary(
                        stage="final",
                        subtotal=final.subtotal,
                        tax=final.tax,
                        total=final.total,
                    ),
                    subtotal=grand.subtotal,
                    tax=grand.tax,
                    total=grand.total,
                    valve_discount=grand.valve_discount,
                    total_after_discount=grand.total_after_discount,
                )
            )

            ground_subtotal += ground.subtotal
            ground_tax += ground.tax
            ground_total += ground.total

            topout_subtotal += topout.subtotal
            topout_tax += topout.tax
            topout_total += topout.total

            final_subtotal += final.subtotal
            final_tax += final.tax
            final_total += final.total

            subtotal += grand.subtotal
            tax += grand.tax
            total += grand.total
            valve_discount += grand.valve_discount
            total_after_discount += grand.total_after_discount

        return ProjectInvoiceSummary(
            project_code=project_code,
            takeoff_count=len(out),
            ground_subtotal=ground_subtotal,
            ground_tax=ground_tax,
            ground_total=ground_total,
            topout_subtotal=topout_subtotal,
            topout_tax=topout_tax,
            topout_total=topout_total,
            final_subtotal=final_subtotal,
            final_tax=final_tax,
            final_total=final_total,
            subtotal=subtotal,
            tax=tax,
            total=total,
            valve_discount=valve_discount,
            total_after_discount=total_after_discount,
            takeoffs=tuple(out),
        )
