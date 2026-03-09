from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.application.diff_takeoff_versions import DiffTakeoffVersions
from app.domain.revision_report import RevisionReport, RevisionReportLine
from app.domain.version_diff import VersionLineDiff, VersionLineState


@dataclass(frozen=True)
class GenerateRevisionReport:
    takeoff_repo: object

    def __call__(self, *, version_a: str, version_b: str) -> RevisionReport:
        diff = DiffTakeoffVersions(takeoff_repo=self.takeoff_repo)(
            version_a=version_a,
            version_b=version_b,
        )

        lines: list[RevisionReportLine] = []

        for ln in diff.lines:
            if ln.change == "unchanged":
                continue

            line_delta = self._line_delta(ln)

            if ln.change == "added":
                new = ln.new
                text = (
                    f"{ln.item_code} | "
                    f"qty={new.qty} | stage={new.stage} | factor={new.factor} | unit_price={new.unit_price}"
                )
            elif ln.change == "removed":
                old = ln.old
                text = (
                    f"{ln.item_code} | "
                    f"qty={old.qty} | stage={old.stage} | factor={old.factor} | unit_price={old.unit_price}"
                )
            else:
                old = ln.old
                new = ln.new
                text = (
                    f"{ln.item_code} | "
                    f"qty: {old.qty} -> {new.qty} | "
                    f"stage: {old.stage} -> {new.stage} | "
                    f"factor: {old.factor} -> {new.factor} | "
                    f"unit_price: {old.unit_price} -> {new.unit_price}"
                )

            lines.append(
                RevisionReportLine(
                    item_code=ln.item_code,
                    section=ln.change,
                    text=text,
                    line_delta=line_delta,
                )
            )

        delta = diff.financial_delta()

        return RevisionReport(
            version_a=diff.version_a,
            version_b=diff.version_b,
            summary=diff.summary(),
            subtotal_a=diff.financial_a.subtotal,
            subtotal_b=diff.financial_b.subtotal,
            subtotal_delta=delta.subtotal,
            tax_a=diff.financial_a.tax,
            tax_b=diff.financial_b.tax,
            tax_delta=delta.tax,
            total_a=diff.financial_a.total,
            total_b=diff.financial_b.total,
            total_delta=delta.total,
            valve_discount_a=diff.financial_a.valve_discount,
            valve_discount_b=diff.financial_b.valve_discount,
            valve_discount_delta=delta.valve_discount,
            after_discount_a=diff.financial_a.total_after_discount,
            after_discount_b=diff.financial_b.total_after_discount,
            after_discount_delta=delta.total_after_discount,
            lines=tuple(lines),
        )

    def _line_subtotal(self, state: VersionLineState | None) -> Decimal:
        if state is None:
            return Decimal("0.00")
        return state.unit_price * state.qty * state.factor

    def _line_delta(self, ln: VersionLineDiff) -> Decimal:
        return self._line_subtotal(ln.new) - self._line_subtotal(ln.old)
