

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List

from app.domain.stage import Stage
from app.domain.totals import (
    TakeoffLineInput,
    calc_stage_totals,
    calc_grand_totals,
)


@dataclass(frozen=True)
class InspectTakeoffResult:
    takeoff_id: str
    project_code: str
    template_code: str
    tax_rate: Decimal
    valve_discount: Decimal
    locked: bool
    line_count: int
    stage_totals: dict
    grand_totals: object
    versions: list


class InspectTakeoff:
    """
    Use case that aggregates the operational state of a takeoff.

    It collects:
    - takeoff metadata
    - lines
    - stage totals
    - grand totals
    - version history
    """

    def __init__(self, *, takeoff_repo, takeoff_line_repo):
        self._takeoff_repo = takeoff_repo
        self._takeoff_line_repo = takeoff_line_repo

    def __call__(self, *, takeoff_id: str) -> InspectTakeoffResult:
        takeoff = self._takeoff_repo.get(takeoff_id=takeoff_id)

        lines = list(self._takeoff_line_repo.list_for_takeoff(takeoff_id=takeoff_id))

        inputs: List[TakeoffLineInput] = []

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

        stage_totals = {}

        for st in (Stage.GROUND, Stage.TOPOUT, Stage.FINAL):
            tt = calc_stage_totals(inputs, stage=st, tax_rate=takeoff.tax_rate)
            stage_totals[st.value] = tt

        grand_totals = calc_grand_totals(
            inputs,
            valve_discount=takeoff.valve_discount,
            tax_rate=takeoff.tax_rate,
        )

        versions = list(self._takeoff_repo.list_versions(takeoff_id=takeoff_id))

        return InspectTakeoffResult(
            takeoff_id=takeoff.takeoff_id,
            project_code=takeoff.project_code,
            template_code=takeoff.template_code,
            tax_rate=takeoff.tax_rate,
            valve_discount=takeoff.valve_discount,
            locked=takeoff.is_locked,
            line_count=len(lines),
            stage_totals=stage_totals,
            grand_totals=grand_totals,
            versions=versions,
        )