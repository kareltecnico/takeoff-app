from __future__ import annotations

from dataclasses import dataclass

from app.domain.stage import Stage
from app.domain.totals import TakeoffLineInput, calc_grand_totals
from app.domain.version_diff import (
    VersionDiffResult,
    VersionFinancialState,
    VersionLineDiff,
    VersionLineState,
)


@dataclass(frozen=True)
class DiffTakeoffVersions:
    """
    Application use-case that compares two immutable takeoff versions.

    It loads snapshot lines from both versions and produces:
    - structural diff grouped by item_code
    - financial totals for each version
    - financial delta between versions
    """

    takeoff_repo: object

    def __call__(self, *, version_a: str, version_b: str) -> VersionDiffResult:
        a_lines = self.takeoff_repo.list_version_lines(version_id=version_a)
        b_lines = self.takeoff_repo.list_version_lines(version_id=version_b)

        a_version = self.takeoff_repo.get_version(version_id=version_a)
        b_version = self.takeoff_repo.get_version(version_id=version_b)

        a_map: dict[str, VersionLineState] = {}
        b_map: dict[str, VersionLineState] = {}

        for ln in a_lines:
            a_map[ln.item_code] = VersionLineState(
                item_code=ln.item_code,
                qty=ln.qty,
                stage=ln.stage,
                factor=ln.factor,
                unit_price=ln.unit_price_snapshot,
            )

        for ln in b_lines:
            b_map[ln.item_code] = VersionLineState(
                item_code=ln.item_code,
                qty=ln.qty,
                stage=ln.stage,
                factor=ln.factor,
                unit_price=ln.unit_price_snapshot,
            )

        all_items = sorted(set(a_map.keys()) | set(b_map.keys()))
        diffs: list[VersionLineDiff] = []

        for item in all_items:
            a = a_map.get(item)
            b = b_map.get(item)

            if a is None and b is not None:
                change = "added"
            elif a is not None and b is None:
                change = "removed"
            else:
                if (
                    a.qty != b.qty
                    or a.stage != b.stage
                    or a.factor != b.factor
                    or a.unit_price != b.unit_price
                ):
                    change = "modified"
                else:
                    change = "unchanged"

            diffs.append(
                VersionLineDiff(
                    item_code=item,
                    change=change,
                    old=a,
                    new=b,
                )
            )

        return VersionDiffResult(
            version_a=version_a,
            version_b=version_b,
            lines=tuple(diffs),
            financial_a=self._build_financial_state(
                a_lines=a_lines,
                tax_rate=a_version.tax_rate_snapshot,
                valve_discount=a_version.valve_discount_snapshot,
            ),
            financial_b=self._build_financial_state(
                a_lines=b_lines,
                tax_rate=b_version.tax_rate_snapshot,
                valve_discount=b_version.valve_discount_snapshot,
            ),
        )

    def _build_financial_state(self, *, a_lines: tuple[object, ...], tax_rate, valve_discount) -> VersionFinancialState:
        inputs: list[TakeoffLineInput] = []
        for ln in a_lines:
            inputs.append(
                TakeoffLineInput(
                    stage=Stage(ln.stage),
                    price=ln.unit_price_snapshot,
                    qty=ln.qty,
                    factor=ln.factor,
                    taxable=ln.taxable_snapshot,
                )
            )

        totals = calc_grand_totals(
            inputs,
            valve_discount=valve_discount,
            tax_rate=tax_rate,
        )
        return VersionFinancialState(
            subtotal=totals.subtotal,
            tax=totals.tax,
            total=totals.total,
            valve_discount=totals.valve_discount,
            total_after_discount=totals.total_after_discount,
        )