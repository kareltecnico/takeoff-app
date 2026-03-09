from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


ChangeType = Literal["added", "removed", "modified", "unchanged"]


@dataclass(frozen=True)
class VersionLineState:
    item_code: str
    qty: Decimal
    stage: str
    factor: Decimal
    unit_price: Decimal


@dataclass(frozen=True)
class VersionLineDiff:
    item_code: str
    change: ChangeType
    old: VersionLineState | None
    new: VersionLineState | None


@dataclass(frozen=True)
class VersionFinancialState:
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    valve_discount: Decimal
    total_after_discount: Decimal


@dataclass(frozen=True)
class VersionDiffResult:
    version_a: str
    version_b: str
    lines: tuple[VersionLineDiff, ...]
    financial_a: VersionFinancialState
    financial_b: VersionFinancialState

    def has_changes(self) -> bool:
        for ln in self.lines:
            if ln.change != "unchanged":
                return True
        return False

    def summary(self) -> dict[str, int]:
        added = 0
        removed = 0
        modified = 0
        unchanged = 0

        for ln in self.lines:
            if ln.change == "added":
                added += 1
            elif ln.change == "removed":
                removed += 1
            elif ln.change == "modified":
                modified += 1
            else:
                unchanged += 1

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged,
        }

    def financial_delta(self) -> VersionFinancialState:
        return VersionFinancialState(
            subtotal=self.financial_b.subtotal - self.financial_a.subtotal,
            tax=self.financial_b.tax - self.financial_a.tax,
            total=self.financial_b.total - self.financial_a.total,
            valve_discount=self.financial_b.valve_discount - self.financial_a.valve_discount,
            total_after_discount=self.financial_b.total_after_discount - self.financial_a.total_after_discount,
        )