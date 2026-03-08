from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from app.application.errors import InvalidInputError
from app.domain.takeoff_record import TakeoffRecord


@dataclass(frozen=True)
class TakeoffVersionRecord:
    version_id: str
    takeoff_id: str
    project_code_snapshot: str
    template_code_snapshot: str
    version_number: int
    notes: str | None
    tax_rate_snapshot: Decimal
    valve_discount_snapshot: Decimal
    created_at: str


@dataclass(frozen=True)
class TakeoffVersionLineSnapshot:
    version_id: str
    item_code: str
    qty: Decimal
    notes: str | None
    description_snapshot: str
    details_snapshot: str | None
    unit_price_snapshot: Decimal
    taxable_snapshot: bool
    stage: str
    factor: Decimal
    sort_order: int
    created_at: str | None


@dataclass(frozen=True)
class SqliteTakeoffRepository:
    conn: sqlite3.Connection

    # -------------------------
    # Takeoffs
    # -------------------------

    def create(self, takeoff: TakeoffRecord) -> None:
        self.conn.execute("BEGIN")
        try:
            self.conn.execute(
                """
                INSERT INTO takeoffs (
                    takeoff_id, project_code, template_code, tax_rate, valve_discount, updated_at
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    takeoff.takeoff_id,
                    takeoff.project_code,
                    takeoff.template_code,
                    str(takeoff.tax_rate),
                    str(takeoff.valve_discount),
                ),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get(self, takeoff_id: str) -> TakeoffRecord:
        row = self.conn.execute(
            """
            SELECT takeoff_id, project_code, template_code, tax_rate, valve_discount, created_at
            FROM takeoffs
            WHERE takeoff_id = ?
            """,
            (takeoff_id,),
        ).fetchone()

        if not row:
            raise InvalidInputError(f"Takeoff not found: {takeoff_id}")

        return TakeoffRecord(
            takeoff_id=str(row["takeoff_id"]),
            project_code=str(row["project_code"]),
            template_code=str(row["template_code"]),
            tax_rate=Decimal(str(row["tax_rate"])),
            valve_discount=Decimal(str(row["valve_discount"])),
            created_at=str(row["created_at"]),
        )

    def find_by_project_template(self, *, project_code: str, template_code: str) -> TakeoffRecord | None:
        row = self.conn.execute(
            """
            SELECT takeoff_id, project_code, template_code, tax_rate, valve_discount, created_at
            FROM takeoffs
            WHERE project_code = ? AND template_code = ?
            """,
            (project_code, template_code),
        ).fetchone()

        if not row:
            return None

        return TakeoffRecord(
            takeoff_id=str(row["takeoff_id"]),
            project_code=str(row["project_code"]),
            template_code=str(row["template_code"]),
            tax_rate=Decimal(str(row["tax_rate"])),
            valve_discount=Decimal(str(row["valve_discount"])),
            created_at=str(row["created_at"]),
        )
    
    def list_for_project(self, project_code: str) -> tuple[TakeoffRecord, ...]:
        rows = self.conn.execute(
            """
            SELECT takeoff_id, project_code, template_code, tax_rate, valve_discount, created_at
            FROM takeoffs
            WHERE project_code = ?
            ORDER BY created_at DESC
            """,
            (project_code,),
        ).fetchall()

        out: list[TakeoffRecord] = []
        for r in rows:
            out.append(
                TakeoffRecord(
                    takeoff_id=str(r["takeoff_id"]),
                    project_code=str(r["project_code"]),
                    template_code=str(r["template_code"]),
                    tax_rate=Decimal(str(r["tax_rate"])),
                    valve_discount=Decimal(str(r["valve_discount"])),
                    created_at=str(r["created_at"]),
                )
            )
        return tuple(out)

    # -------------------------
    # Versioning / Snapshots
    # -------------------------

    def create_snapshot_version(self, *, takeoff_id: str, notes: str | None = None) -> str:
        """Create an immutable snapshot version for an existing takeoff.

        Atomic transaction:
          - insert takeoff_versions row
          - copy all current takeoff_lines into takeoff_version_lines

        This enables reproducible rendering later.
        """

        # Validate exists + get pinned context
        t = self.get(takeoff_id=takeoff_id)

        project_code_snapshot = t.project_code
        template_code_snapshot = t.template_code
        tax_rate_snapshot = t.tax_rate
        valve_discount_snapshot = t.valve_discount

        row = self.conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) FROM takeoff_versions WHERE takeoff_id = ?",
            (takeoff_id,),
        ).fetchone()
        next_version = int(row[0]) + 1

        version_id = str(uuid4())

        self.conn.execute("BEGIN")
        try:
            self.conn.execute(
                """
                INSERT INTO takeoff_versions (
                    version_id,
                    takeoff_id,
                    project_code_snapshot,
                    template_code_snapshot,
                    version_number,
                    notes,
                    tax_rate_snapshot,
                    valve_discount_snapshot,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    version_id,
                    takeoff_id,
                    project_code_snapshot,
                    template_code_snapshot,
                    next_version,
                    notes,
                    str(tax_rate_snapshot),
                    str(valve_discount_snapshot),
                ),
            )

            rows = self.conn.execute(
                """
                SELECT
                    item_code,
                    qty,
                    notes,
                    description_snapshot,
                    details_snapshot,
                    unit_price_snapshot,
                    taxable_snapshot,
                    COALESCE(stage, 'final') AS stage,
                    COALESCE(factor, '1.0') AS factor,
                    COALESCE(sort_order, 0) AS sort_order
                FROM takeoff_lines
                WHERE takeoff_id = ?
                """,
                (takeoff_id,),
            ).fetchall()

            for r in rows:
                self.conn.execute(
                    """
                    INSERT INTO takeoff_version_lines (
                        version_id,
                        item_code,
                        qty,
                        notes,
                        description_snapshot,
                        details_snapshot,
                        unit_price_snapshot,
                        taxable_snapshot,
                        stage,
                        factor,
                        sort_order,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        version_id,
                        str(r["item_code"]),
                        str(Decimal(str(r["qty"]))),
                        str(r["notes"]) if r["notes"] is not None else None,
                        str(r["description_snapshot"]),
                        str(r["details_snapshot"]) if r["details_snapshot"] is not None else None,
                        str(Decimal(str(r["unit_price_snapshot"]))),
                        int(r["taxable_snapshot"]),
                        str(r["stage"] or "final"),
                        str(Decimal(str(r["factor"] or "1.0"))),
                        int(r["sort_order"] or 0),
                    ),
                )

            self.conn.commit()
            return version_id
        except Exception:
            self.conn.rollback()
            raise

    def list_versions(self, *, takeoff_id: str) -> tuple[TakeoffVersionRecord, ...]:
        rows = self.conn.execute(
            """
            SELECT
                version_id,
                takeoff_id,
                project_code_snapshot,
                template_code_snapshot,
                version_number,
                notes,
                tax_rate_snapshot,
                valve_discount_snapshot,
                created_at
            FROM takeoff_versions
            WHERE takeoff_id = ?
            ORDER BY version_number DESC
            """,
            (takeoff_id,),
        ).fetchall()

        out: list[TakeoffVersionRecord] = []
        for r in rows:
            out.append(
                TakeoffVersionRecord(
                    version_id=str(r["version_id"]),
                    takeoff_id=str(r["takeoff_id"]),
                    project_code_snapshot=str(r["project_code_snapshot"]),
                    template_code_snapshot=str(r["template_code_snapshot"]),
                    version_number=int(r["version_number"]),
                    notes=str(r["notes"]) if r["notes"] is not None else None,
                    tax_rate_snapshot=Decimal(str(r["tax_rate_snapshot"])),
                    valve_discount_snapshot=Decimal(str(r["valve_discount_snapshot"])),
                    created_at=str(r["created_at"]),
                )
            )
        return tuple(out)

    def get_version(self, *, version_id: str) -> TakeoffVersionRecord:
        r = self.conn.execute(
            """
            SELECT
                version_id,
                takeoff_id,
                project_code_snapshot,
                template_code_snapshot,
                version_number,
                notes,
                tax_rate_snapshot,
                valve_discount_snapshot,
                created_at
            FROM takeoff_versions
            WHERE version_id = ?
            """,
            (version_id,),
        ).fetchone()

        if not r:
            raise InvalidInputError(f"Takeoff version not found: {version_id}")

        return TakeoffVersionRecord(
            version_id=str(r["version_id"]),
            takeoff_id=str(r["takeoff_id"]),
            project_code_snapshot=str(r["project_code_snapshot"]),
            template_code_snapshot=str(r["template_code_snapshot"]),
            version_number=int(r["version_number"]),
            notes=str(r["notes"]) if r["notes"] is not None else None,
            tax_rate_snapshot=Decimal(str(r["tax_rate_snapshot"])),
            valve_discount_snapshot=Decimal(str(r["valve_discount_snapshot"])),
            created_at=str(r["created_at"]),
        )

    def list_version_lines(self, *, version_id: str) -> tuple[TakeoffVersionLineSnapshot, ...]:
        rows = self.conn.execute(
            """
            SELECT
                version_id,
                item_code,
                qty,
                notes,
                description_snapshot,
                details_snapshot,
                unit_price_snapshot,
                taxable_snapshot,
                COALESCE(stage, 'final') AS stage,
                COALESCE(factor, '1.0') AS factor,
                COALESCE(sort_order, 0) AS sort_order,
                created_at
            FROM takeoff_version_lines
            WHERE version_id = ?
            ORDER BY
                CASE COALESCE(stage, 'final')
                    WHEN 'ground' THEN 0
                    WHEN 'topout' THEN 1
                    WHEN 'final' THEN 2
                    ELSE 99
                END,
                sort_order,
                item_code
            """,
            (version_id,),
        ).fetchall()

        out: list[TakeoffVersionLineSnapshot] = []
        for r in rows:
            out.append(
                TakeoffVersionLineSnapshot(
                    version_id=str(r["version_id"]),
                    item_code=str(r["item_code"]),
                    qty=Decimal(str(r["qty"])),
                    notes=str(r["notes"]) if r["notes"] is not None else None,
                    description_snapshot=str(r["description_snapshot"]),
                    details_snapshot=str(r["details_snapshot"]) if r["details_snapshot"] is not None else None,
                    unit_price_snapshot=Decimal(str(r["unit_price_snapshot"])),
                    taxable_snapshot=bool(int(r["taxable_snapshot"])),
                    stage=str(r["stage"] or "final"),
                    factor=Decimal(str(r["factor"] or "1.0")),
                    sort_order=int(r["sort_order"] or 0),
                    created_at=str(r["created_at"]) if r["created_at"] is not None else None,
                )
            )
        return tuple(out)