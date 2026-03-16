from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.application.repositories.template_fixture_mapping_repository import (
    TemplateFixtureMappingRepository,
)
from app.domain.fixture_mapping import (
    FixtureQuantityRef,
    FixtureQuantitySourceKind,
    TemplateFixtureMappingRule,
)
from app.domain.stage import Stage


def _b(value: bool) -> int:
    return 1 if value else 0


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, (str, bytes, bytearray)):
        return int(value) != 0
    raise TypeError(f"Expected boolean-ish SQLite value, got {type(value).__name__}")


@dataclass(frozen=True)
class SqliteTemplateFixtureMappingRepository(TemplateFixtureMappingRepository):
    conn: sqlite3.Connection

    def add(self, rule: TemplateFixtureMappingRule) -> None:
        if not rule.mapping_id.strip():
            raise InvalidInputError("TemplateFixtureMappingRule.mapping_id cannot be empty")
        if not rule.template_code.strip():
            raise InvalidInputError("TemplateFixtureMappingRule.template_code cannot be empty")
        if not rule.item_code.strip():
            raise InvalidInputError("TemplateFixtureMappingRule.item_code cannot be empty")
        if rule.qty_multiplier <= Decimal("0"):
            raise InvalidInputError("TemplateFixtureMappingRule.qty_multiplier must be > 0")
        if rule.factor <= Decimal("0"):
            raise InvalidInputError("TemplateFixtureMappingRule.factor must be > 0")
        if rule.sort_order < 0:
            raise InvalidInputError("TemplateFixtureMappingRule.sort_order must be >= 0")
        if not isinstance(rule.stage, Stage):
            raise InvalidInputError("TemplateFixtureMappingRule.stage must be a Stage enum value")

        ref = rule.quantity_ref
        if ref.source_kind == FixtureQuantitySourceKind.CONSTANT:
            if ref.constant_qty is None:
                raise InvalidInputError("Constant quantity refs require constant_qty")
        else:
            if not ref.source_name:
                raise InvalidInputError("Non-constant quantity refs require source_name")

        try:
            self.conn.execute(
                """
                INSERT INTO template_fixture_mappings (
                    mapping_id,
                    template_code,
                    source_kind,
                    source_name,
                    constant_qty,
                    item_code,
                    qty_multiplier,
                    stage,
                    factor,
                    sort_order,
                    notes,
                    is_active,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    rule.mapping_id,
                    rule.template_code,
                    rule.quantity_ref.source_kind.value,
                    rule.quantity_ref.source_name,
                    str(rule.quantity_ref.constant_qty)
                    if rule.quantity_ref.constant_qty is not None
                    else None,
                    rule.item_code,
                    str(rule.qty_multiplier),
                    rule.stage.value,
                    str(rule.factor),
                    int(rule.sort_order),
                    rule.notes,
                    _b(rule.is_active),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise InvalidInputError(
                "Template fixture mapping constraint failed "
                f"(mapping_id={rule.mapping_id!r}, template={rule.template_code!r}, "
                f"item={rule.item_code!r})"
            ) from exc

        self.conn.commit()

    def get(self, mapping_id: str) -> TemplateFixtureMappingRule:
        row = self.conn.execute(
            """
            SELECT
                mapping_id,
                template_code,
                source_kind,
                source_name,
                constant_qty,
                item_code,
                qty_multiplier,
                stage,
                factor,
                sort_order,
                notes,
                is_active
            FROM template_fixture_mappings
            WHERE mapping_id = ?
            """,
            (mapping_id,),
        ).fetchone()

        if row is None:
            raise InvalidInputError(f"Template fixture mapping not found: {mapping_id}")

        return self._row_to_rule(row)

    def list_for_template(
        self,
        template_code: str,
        *,
        include_inactive: bool = False,
    ) -> tuple[TemplateFixtureMappingRule, ...]:
        if include_inactive:
            rows = self.conn.execute(
                """
                SELECT
                    mapping_id,
                    template_code,
                    source_kind,
                    source_name,
                    constant_qty,
                    item_code,
                    qty_multiplier,
                    stage,
                    factor,
                    sort_order,
                    notes,
                    is_active
                FROM template_fixture_mappings
                WHERE template_code = ?
                ORDER BY sort_order, mapping_id
                """,
                (template_code,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT
                    mapping_id,
                    template_code,
                    source_kind,
                    source_name,
                    constant_qty,
                    item_code,
                    qty_multiplier,
                    stage,
                    factor,
                    sort_order,
                    notes,
                    is_active
                FROM template_fixture_mappings
                WHERE template_code = ?
                  AND is_active = 1
                ORDER BY sort_order, mapping_id
                """,
                (template_code,),
            ).fetchall()

        return tuple(self._row_to_rule(row) for row in rows)

    def _row_to_rule(self, row: sqlite3.Row) -> TemplateFixtureMappingRule:
        constant_qty = (
            Decimal(str(row["constant_qty"]))
            if row["constant_qty"] is not None
            else None
        )
        return TemplateFixtureMappingRule(
            mapping_id=str(row["mapping_id"]),
            template_code=str(row["template_code"]),
            quantity_ref=FixtureQuantityRef(
                source_kind=FixtureQuantitySourceKind(str(row["source_kind"])),
                source_name=row["source_name"],
                constant_qty=constant_qty,
            ),
            item_code=str(row["item_code"]),
            qty_multiplier=Decimal(str(row["qty_multiplier"])),
            stage=Stage(str(row["stage"])),
            factor=Decimal(str(row["factor"])),
            sort_order=int(row["sort_order"]),
            notes=row["notes"],
            is_active=_bool(row["is_active"]),
        )
