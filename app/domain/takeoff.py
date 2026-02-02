from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.stage import Stage
from app.domain.takeoff_line import TakeoffLine
from app.domain.totals import GrandTotals, TakeoffLineInput, calc_grand_totals, calc_stage_totals


@dataclass(frozen=True)
class TakeoffHeader:
    project_name: str
    contractor_name: str
    model_group_display: str
    models: tuple[str, ...]
    stories: int


@dataclass(frozen=True)
class Takeoff:
    header: TakeoffHeader
    lines: tuple[TakeoffLine, ...]
    valve_discount: Decimal = Decimal("-112.99")
    tax_rate: Decimal = Decimal("0.07")

    def lines_for_stage(self, stage: Stage) -> tuple[TakeoffLine, ...]:
        """Lines for a stage, sorted by sort_order (stable PDF layout)."""
        stage_lines = [ln for ln in self.lines if ln.stage == stage]
        stage_lines.sort(key=lambda ln: ln.sort_order)
        return tuple(stage_lines)

    def _as_inputs(self) -> list[TakeoffLineInput]:
        """Convert lines to calculation inputs (stage/price/qty/factor/taxable)."""
        inputs: list[TakeoffLineInput] = []
        for ln in self.lines:
            inputs.append(
                TakeoffLineInput(
                    stage=ln.stage,
                    price=ln.item.unit_price,
                    qty=ln.qty,
                    factor=ln.factor,
                    taxable=ln.item.taxable,
                )
            )
        return inputs

    def stage_totals(self, stage: Stage) -> tuple[Decimal, Decimal, Decimal]:
        """Return (subtotal, tax, total) for a specific stage."""
        t = calc_stage_totals(self._as_inputs(), stage=stage, tax_rate=self.tax_rate)
        return (t.subtotal, t.tax, t.total)

    def grand_totals(self) -> GrandTotals:
        """Return grand totals across all stages, including valve discount."""
        return calc_grand_totals(
            self._as_inputs(),
            valve_discount=self.valve_discount,
            tax_rate=self.tax_rate,
        )
