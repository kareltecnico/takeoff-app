from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.derived_quantities import DerivedQuantities
from app.domain.plan_reading_input import PlanReadingInput
from app.domain.stage import Stage


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        return Decimal(value)
    raise TypeError(f"Unsupported quantity value type: {type(value).__name__}")


class FixtureQuantitySourceKind(StrEnum):
    DERIVED = "derived"
    PLAN = "plan"
    CONSTANT = "constant"


@dataclass(frozen=True)
class FixtureQuantityRef:
    source_kind: FixtureQuantitySourceKind
    source_name: str | None = None
    constant_qty: Decimal | None = None

    def resolve(
        self,
        *,
        plan: PlanReadingInput,
        derived: DerivedQuantities,
    ) -> Decimal:
        if self.source_kind == FixtureQuantitySourceKind.CONSTANT:
            if self.constant_qty is None:
                raise ValueError("constant_qty is required for constant quantity refs")
            return _as_decimal(self.constant_qty)

        if not self.source_name:
            raise ValueError("source_name is required for non-constant quantity refs")

        source = derived if self.source_kind == FixtureQuantitySourceKind.DERIVED else plan
        try:
            value = getattr(source, self.source_name)
        except AttributeError as exc:
            raise ValueError(
                f"Unknown {self.source_kind.value} quantity source: {self.source_name}"
            ) from exc
        return _as_decimal(value)


@dataclass(frozen=True)
class TemplateFixtureMappingRule:
    mapping_id: str
    template_code: str
    quantity_ref: FixtureQuantityRef
    item_code: str
    qty_multiplier: Decimal = Decimal("1.0")
    stage: Stage = Stage.FINAL
    factor: Decimal = Decimal("1.0")
    sort_order: int = 0
    notes: str | None = None
    is_active: bool = True


@dataclass(frozen=True)
class ProjectFixtureOverride:
    project_code: str
    mapping_id: str
    is_disabled: bool = False
    item_code_override: str | None = None
    notes_override: str | None = None


@dataclass(frozen=True)
class EffectiveFixtureMapping:
    mapping_id: str
    template_code: str
    quantity_ref: FixtureQuantityRef
    item_code: str
    qty_multiplier: Decimal
    stage: Stage
    factor: Decimal
    sort_order: int
    notes: str | None


@dataclass(frozen=True)
class MappedTakeoffLine:
    mapping_id: str
    item_code: str
    qty: Decimal
    stage: Stage
    factor: Decimal
    sort_order: int
    notes: str | None


@dataclass(frozen=True)
class FixtureMappingResolver:
    def resolve_effective_rule(
        self,
        *,
        rule: TemplateFixtureMappingRule,
        override: ProjectFixtureOverride | None,
    ) -> EffectiveFixtureMapping | None:
        if not rule.is_active:
            return None
        if override is not None and override.is_disabled:
            return None

        item_code = (
            override.item_code_override
            if override is not None and override.item_code_override
            else rule.item_code
        )
        notes = (
            override.notes_override
            if override is not None and override.notes_override is not None
            else rule.notes
        )

        return EffectiveFixtureMapping(
            mapping_id=rule.mapping_id,
            template_code=rule.template_code,
            quantity_ref=rule.quantity_ref,
            item_code=item_code,
            qty_multiplier=rule.qty_multiplier,
            stage=rule.stage,
            factor=rule.factor,
            sort_order=rule.sort_order,
            notes=notes,
        )

    def resolve(
        self,
        *,
        project_code: str,
        rules: tuple[TemplateFixtureMappingRule, ...],
        overrides: tuple[ProjectFixtureOverride, ...],
        plan: PlanReadingInput,
        derived: DerivedQuantities,
    ) -> tuple[MappedTakeoffLine, ...]:
        overrides_by_mapping_id = {
            ov.mapping_id: ov
            for ov in overrides
            if ov.project_code == project_code
        }

        out: list[MappedTakeoffLine] = []
        for rule in rules:
            effective = self.resolve_effective_rule(
                rule=rule,
                override=overrides_by_mapping_id.get(rule.mapping_id),
            )
            if effective is None:
                continue

            source_qty = effective.quantity_ref.resolve(plan=plan, derived=derived)
            qty = source_qty * effective.qty_multiplier
            if qty == Decimal("0"):
                continue

            out.append(
                MappedTakeoffLine(
                    mapping_id=effective.mapping_id,
                    item_code=effective.item_code,
                    qty=qty,
                    stage=effective.stage,
                    factor=effective.factor,
                    sort_order=effective.sort_order,
                    notes=effective.notes,
                )
            )

        return tuple(out)
