from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RevisionReportLine:
    item_code: str
    section: str  # added / removed / modified
    text: str
    line_delta: Decimal


@dataclass(frozen=True)
class RevisionReport:
    version_a: str
    version_b: str
    summary: dict[str, int]
    subtotal_a: Decimal
    subtotal_b: Decimal
    subtotal_delta: Decimal
    tax_a: Decimal
    tax_b: Decimal
    tax_delta: Decimal
    total_a: Decimal
    total_b: Decimal
    total_delta: Decimal
    valve_discount_a: Decimal
    valve_discount_b: Decimal
    valve_discount_delta: Decimal
    after_discount_a: Decimal
    after_discount_b: Decimal
    after_discount_delta: Decimal
    lines: tuple[RevisionReportLine, ...]

    def to_text(self) -> str:
        parts: list[str] = []

        parts.append("REVISION REPORT")
        parts.append(f"version_a={self.version_a}")
        parts.append(f"version_b={self.version_b}")
        parts.append("")

        parts.append("SUMMARY")
        parts.append(
            f"added={self.summary['added']} | "
            f"removed={self.summary['removed']} | "
            f"modified={self.summary['modified']} | "
            f"unchanged={self.summary['unchanged']}"
        )
        parts.append("")

        parts.append("FINANCIAL")
        parts.append(
            f"subtotal: {self.subtotal_a:.2f} -> {self.subtotal_b:.2f} | delta={self.subtotal_delta:.2f}"
        )
        parts.append(
            f"tax: {self.tax_a:.2f} -> {self.tax_b:.2f} | delta={self.tax_delta:.2f}"
        )
        parts.append(
            f"total: {self.total_a:.2f} -> {self.total_b:.2f} | delta={self.total_delta:.2f}"
        )
        parts.append(
            f"valve_discount: {self.valve_discount_a:.2f} -> {self.valve_discount_b:.2f} | "
            f"delta={self.valve_discount_delta:.2f}"
        )
        parts.append(
            f"after_discount: {self.after_discount_a:.2f} -> {self.after_discount_b:.2f} | "
            f"delta={self.after_discount_delta:.2f}"
        )
        parts.append("")

        for section in ("added", "removed", "modified"):
            section_lines = [ln for ln in self.lines if ln.section == section]
            if not section_lines:
                continue

            parts.append(section.upper())
            for ln in section_lines:
                parts.append(f"{ln.text} | line_delta={ln.line_delta:.2f}")
            parts.append("")

        return "\n".join(parts).rstrip() + "\n"
