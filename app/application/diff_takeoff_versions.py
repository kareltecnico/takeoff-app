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

    def _line_identity(self, ln: object) -> tuple[str, str]:
        mapping_id = getattr(ln, "mapping_id", None)
        if mapping_id:
            return (str(mapping_id), "mapping_id")
        return (str(ln.item_code), "legacy_item_code")

    def _build_line_maps(
        self,
        *,
        lines: tuple[object, ...],
        version_label: str,
    ) -> tuple[dict[str, VersionLineState], set[str], list[str]]:
        mapped: dict[str, VersionLineState] = {}
        legacy_counts: dict[str, int] = {}

        for ln in lines:
            comparison_key, key_kind = self._line_identity(ln)
            if key_kind == "mapping_id":
                mapped[comparison_key] = VersionLineState(
                    comparison_key=comparison_key,
                    comparison_key_kind=key_kind,
                    mapping_id=getattr(ln, "mapping_id", None),
                    item_code=ln.item_code,
                    qty=ln.qty,
                    stage=ln.stage,
                    factor=ln.factor,
                    unit_price=ln.unit_price_snapshot,
                )
            else:
                legacy_counts[comparison_key] = legacy_counts.get(comparison_key, 0) + 1

        warnings: list[str] = []
        duplicate_legacy_keys = sorted(
            item_code
            for item_code, count in legacy_counts.items()
            if count > 1
        )
        if duplicate_legacy_keys:
            joined = ", ".join(duplicate_legacy_keys)
            warnings.append(
                f"{version_label}: structural diff is not trustworthy for duplicate legacy "
                f"item_code fallback keys without mapping_id ({joined})"
            )

        for ln in lines:
            comparison_key, key_kind = self._line_identity(ln)
            if key_kind != "legacy_item_code":
                continue
            if legacy_counts.get(comparison_key, 0) != 1:
                continue
            mapped[comparison_key] = VersionLineState(
                comparison_key=comparison_key,
                comparison_key_kind=key_kind,
                mapping_id=None,
                item_code=ln.item_code,
                qty=ln.qty,
                stage=ln.stage,
                factor=ln.factor,
                unit_price=ln.unit_price_snapshot,
            )

        return mapped, set(duplicate_legacy_keys), warnings

    def __call__(self, *, version_a: str, version_b: str) -> VersionDiffResult:
        a_lines = self.takeoff_repo.list_version_lines(version_id=version_a)
        b_lines = self.takeoff_repo.list_version_lines(version_id=version_b)

        a_version = self.takeoff_repo.get_version(version_id=version_a)
        b_version = self.takeoff_repo.get_version(version_id=version_b)

        a_map, a_duplicated_legacy_keys, warnings_a = self._build_line_maps(
            lines=a_lines,
            version_label=f"version_a={version_a}",
        )
        b_map, b_duplicated_legacy_keys, warnings_b = self._build_line_maps(
            lines=b_lines,
            version_label=f"version_b={version_b}",
        )
        warnings = tuple(warnings_a + warnings_b)
        guardrail_triggered = bool(warnings)

        ambiguous_keys = a_duplicated_legacy_keys | b_duplicated_legacy_keys
        for key in ambiguous_keys:
            a_map.pop(key, None)
            b_map.pop(key, None)

        all_items = sorted(set(a_map.keys()) | set(b_map.keys()))
        diffs: list[VersionLineDiff] = []

        for item in all_items:
            a = a_map.get(item)
            b = b_map.get(item)
            effective = b if b is not None else a
            if effective is None:
                continue

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
                    comparison_key=item,
                    comparison_key_kind=effective.comparison_key_kind,
                    item_code=effective.item_code,
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
            guardrail_triggered=guardrail_triggered,
            warnings=warnings,
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
