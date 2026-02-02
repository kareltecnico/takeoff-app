from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.money import LineTotals, calc_line_totals, q2
from app.domain.stage import Stage


@dataclass(frozen=True)
class TakeoffLineInput:
    stage: Stage
    price: Decimal
    qty: Decimal
    factor: Decimal
    taxable: bool


@dataclass(frozen=True)
class StageTotals:
    subtotal: Decimal
    tax: Decimal
    total: Decimal


@dataclass(frozen=True)
class GrandTotals:
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    valve_discount: Decimal
    total_after_discount: Decimal


def calc_stage_totals(
    lines: list[TakeoffLineInput],
    *,
    stage: Stage,
    tax_rate: Decimal = Decimal("0.07"),
) -> StageTotals:
    stage_lines = [ln for ln in lines if ln.stage == stage]

    subtotal = Decimal("0.00")
    tax = Decimal("0.00")

    for ln in stage_lines:
        t: LineTotals = calc_line_totals(
            price=ln.price,
            qty=ln.qty,
            factor=ln.factor,
            taxable=ln.taxable,
            tax_rate=tax_rate,
        )
        subtotal += t.subtotal
        tax += t.tax

    subtotal = q2(subtotal)
    tax = q2(tax)
    total = q2(subtotal + tax)
    return StageTotals(subtotal=subtotal, tax=tax, total=total)


def calc_grand_totals(
    lines: list[TakeoffLineInput],
    *,
    valve_discount: Decimal = Decimal("-112.99"),
    tax_rate: Decimal = Decimal("0.07"),
) -> GrandTotals:
    ground = calc_stage_totals(lines, stage=Stage.GROUND, tax_rate=tax_rate)
    topout = calc_stage_totals(lines, stage=Stage.TOPOUT, tax_rate=tax_rate)
    final = calc_stage_totals(lines, stage=Stage.FINAL, tax_rate=tax_rate)

    subtotal = q2(ground.subtotal + topout.subtotal + final.subtotal)
    tax = q2(ground.tax + topout.tax + final.tax)
    total = q2(subtotal + tax)
    total_after_discount = q2(total + valve_discount)

    return GrandTotals(
        subtotal=subtotal,
        tax=tax,
        total=total,
        valve_discount=valve_discount,
        total_after_discount=total_after_discount,
    )
