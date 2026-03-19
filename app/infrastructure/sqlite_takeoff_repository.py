from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4
import hashlib

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
    created_by: str | None
    reason: str | None
    tax_rate_snapshot: Decimal
    valve_discount_snapshot: Decimal
    integrity_hash: str
    integrity_schema_version: int
    created_at: str


@dataclass(frozen=True)
class TakeoffVersionLineSnapshot:
    version_line_id: str | None
    version_id: str
    item_code: str
    mapping_id: str | None
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
                    takeoff_id, project_code, template_code, tax_rate, valve_discount, is_locked, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    takeoff.takeoff_id,
                    takeoff.project_code,
                    takeoff.template_code,
                    str(takeoff.tax_rate),
                    str(takeoff.valve_discount),
                    1 if takeoff.is_locked else 0,
                ),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get(self, takeoff_id: str) -> TakeoffRecord:
        row = self.conn.execute(
            """
            SELECT takeoff_id, project_code, template_code, tax_rate, valve_discount, is_locked, created_at
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
            is_locked=bool(int(row["is_locked"])),
            created_at=str(row["created_at"]),
        )

    def find_by_project_template(self, *, project_code: str, template_code: str) -> TakeoffRecord | None:
        row = self.conn.execute(
            """
            SELECT takeoff_id, project_code, template_code, tax_rate, valve_discount, is_locked, created_at
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
            is_locked=bool(int(row["is_locked"])),
            created_at=str(row["created_at"]),
        )
    
    def list_for_project(self, project_code: str) -> tuple[TakeoffRecord, ...]:
        rows = self.conn.execute(
            """
            SELECT takeoff_id, project_code, template_code, tax_rate, valve_discount, is_locked, created_at
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
                    is_locked=bool(int(r["is_locked"])),
                    created_at=str(r["created_at"]),
                )
            )
        return tuple(out)

    def set_locked(self, *, takeoff_id: str, is_locked: bool) -> None:
        self.get(takeoff_id=takeoff_id)  # validate existence
        self.conn.execute(
            """
            UPDATE takeoffs
            SET is_locked = ?, updated_at = datetime('now')
            WHERE takeoff_id = ?
            """,
            (1 if is_locked else 0, takeoff_id),
        )
        self.conn.commit()

    def lock(self, *, takeoff_id: str) -> None:
        self.set_locked(takeoff_id=takeoff_id, is_locked=True)

    def unlock(self, *, takeoff_id: str) -> None:
        self.set_locked(takeoff_id=takeoff_id, is_locked=False)

    def _canonical_version_header(
        self,
        *,
        takeoff_id: str,
        project_code_snapshot: str,
        template_code_snapshot: str,
        tax_rate_snapshot: Decimal,
        valve_discount_snapshot: Decimal,
    ) -> tuple[str, str, str, str, str]:
        return (
            str(takeoff_id),
            str(project_code_snapshot),
            str(template_code_snapshot),
            str(Decimal(str(tax_rate_snapshot))),
            str(Decimal(str(valve_discount_snapshot))),
        )

    def _build_integrity_hash(
        self,
        *,
        takeoff_id: str,
        project_code_snapshot: str,
        template_code_snapshot: str,
        tax_rate_snapshot: Decimal,
        valve_discount_snapshot: Decimal,
        rows: list[dict[str, str]],
    ) -> str:
        hash_builder = hashlib.sha256()

        header = self._canonical_version_header(
            takeoff_id=takeoff_id,
            project_code_snapshot=project_code_snapshot,
            template_code_snapshot=template_code_snapshot,
            tax_rate_snapshot=tax_rate_snapshot,
            valve_discount_snapshot=valve_discount_snapshot,
        )
        for part in header:
            hash_builder.update(part.encode())

        def _sort_key(row: dict[str, str]) -> tuple[str, ...]:
            version_line_id = row.get("version_line_id")
            if version_line_id:
                return ("0", version_line_id)
            return (
                "1",
                row["item_code"],
                row.get("stage", ""),
                row.get("sort_order", ""),
                row.get("qty", ""),
                row.get("factor", ""),
                row.get("unit_price_snapshot", ""),
                row.get("description_snapshot", "") or "",
                row.get("notes", "") or "",
            )

        for r in sorted(rows, key=_sort_key):
            hash_builder.update(r["item_code"].encode())
            hash_builder.update(r["qty"].encode())
            hash_builder.update(r["unit_price_snapshot"].encode())
            hash_builder.update(r["taxable_snapshot"].encode())
            hash_builder.update(r["stage"].encode())
            hash_builder.update(r["factor"].encode())
            hash_builder.update(r["sort_order"].encode())
            # schema v2: include full snapshot fields
            if "description_snapshot" in r:
                hash_builder.update((r["description_snapshot"] or "").encode())
            if "details_snapshot" in r:
                hash_builder.update((r["details_snapshot"] or "").encode())
            if "notes" in r:
                hash_builder.update((r["notes"] or "").encode())

        return hash_builder.hexdigest()

    # -------------------------
    # Versioning / Snapshots
    # -------------------------

    def create_snapshot_version(
        self,
        *,
        takeoff_id: str,
        notes: str | None = None,
        created_by: str | None = None,
        reason: str | None = None,
    ) -> str:
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
        normalized_created_by = str(created_by).strip() if created_by is not None else None
        if normalized_created_by == "":
            normalized_created_by = None

        normalized_reason = str(reason).strip() if reason is not None else None
        if normalized_reason == "":
            normalized_reason = None

        # Backward compatibility: if caller only sends notes, use it as reason too.
        if normalized_reason is None and notes is not None:
            stripped_notes = str(notes).strip()
            normalized_reason = stripped_notes or None

        self.conn.execute("BEGIN")
        try:
            raw_rows = self.conn.execute(
                """
                SELECT
                    line_id,
                    item_code,
                    mapping_id,
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

            rows: list[dict[str, str | None]] = []
            for r in raw_rows:
                rows.append(
                    {
                        "line_id": str(r["line_id"]),
                        "item_code": str(r["item_code"]),
                        "mapping_id": str(r["mapping_id"]) if r["mapping_id"] is not None else None,
                        "qty": str(Decimal(str(r["qty"]))),
                        "notes": str(r["notes"]) if r["notes"] is not None else None,
                        "description_snapshot": str(r["description_snapshot"]),
                        "details_snapshot": str(r["details_snapshot"]) if r["details_snapshot"] is not None else None,
                        "unit_price_snapshot": str(Decimal(str(r["unit_price_snapshot"]))),
                        "taxable_snapshot": str(int(r["taxable_snapshot"])),
                        "stage": str(r["stage"] or "final"),
                        "factor": str(Decimal(str(r["factor"] or "1.0"))),
                        "sort_order": str(int(r["sort_order"] or 0)),
                    }
                )

            integrity_hash = ""

            self.conn.execute(
                """
                INSERT INTO takeoff_versions (
                    version_id,
                    takeoff_id,
                    project_code_snapshot,
                    template_code_snapshot,
                    version_number,
                    notes,
                    created_by,
                    reason,
                    tax_rate_snapshot,
                    valve_discount_snapshot,
                    integrity_hash,
                    integrity_schema_version,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    version_id,
                    takeoff_id,
                    project_code_snapshot,
                    template_code_snapshot,
                    next_version,
                    notes,
                    normalized_created_by,
                    normalized_reason,
                    str(tax_rate_snapshot),
                    str(valve_discount_snapshot),
                    integrity_hash,
                    3,
                ),
            )

            for r in rows:
                self.conn.execute(
                    """
                    INSERT INTO takeoff_version_lines (
                        version_line_id,
                        version_id,
                        item_code,
                        mapping_id,
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        uuid4().hex,
                        version_id,
                        str(r["item_code"]),
                        r["mapping_id"],
                        str(r["qty"]),
                        r["notes"],
                        str(r["description_snapshot"]),
                        r["details_snapshot"],
                        str(r["unit_price_snapshot"]),
                        int(str(r["taxable_snapshot"])),
                        str(r["stage"]),
                        str(r["factor"]),
                        int(str(r["sort_order"])),
                    ),
                )

            # Now fetch the persisted rows and compute the canonical integrity hash
            persisted_rows_raw = self.conn.execute(
                """
                SELECT
                    version_line_id,
                    item_code,
                    mapping_id,
                    qty,
                    notes,
                    description_snapshot,
                    details_snapshot,
                    unit_price_snapshot,
                    taxable_snapshot,
                    COALESCE(stage, 'final') AS stage,
                    COALESCE(factor, '1.0') AS factor,
                    COALESCE(sort_order, 0) AS sort_order
                FROM takeoff_version_lines
                WHERE version_id = ?
                """,
                (version_id,),
            ).fetchall()

            persisted_rows = [
                {
                    "version_line_id": str(r["version_line_id"]),
                    "item_code": str(r["item_code"]),
                    "mapping_id": str(r["mapping_id"]) if r["mapping_id"] is not None else None,
                    "qty": str(r["qty"]),
                    "notes": str(r["notes"]) if r["notes"] is not None else None,
                    "description_snapshot": str(r["description_snapshot"]),
                    "details_snapshot": str(r["details_snapshot"]) if r["details_snapshot"] is not None else None,
                    "unit_price_snapshot": str(r["unit_price_snapshot"]),
                    "taxable_snapshot": str(int(r["taxable_snapshot"])),
                    "stage": str(r["stage"] or "final"),
                    "factor": str(r["factor"] or "1.0"),
                    "sort_order": str(int(r["sort_order"] or 0)),
                }
                for r in persisted_rows_raw
            ]

            integrity_hash = self._build_integrity_hash(
                takeoff_id=takeoff_id,
                project_code_snapshot=project_code_snapshot,
                template_code_snapshot=template_code_snapshot,
                tax_rate_snapshot=tax_rate_snapshot,
                valve_discount_snapshot=valve_discount_snapshot,
                rows=persisted_rows,
            )

            self.conn.execute(
                "UPDATE takeoff_versions SET integrity_hash = ? WHERE version_id = ?",
                (integrity_hash, version_id),
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
                created_by,
                reason,
                tax_rate_snapshot,
                valve_discount_snapshot,
                integrity_hash,
                integrity_schema_version,
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
                    created_by=str(r["created_by"]) if r["created_by"] is not None else None,
                    reason=str(r["reason"]) if r["reason"] is not None else None,
                    tax_rate_snapshot=Decimal(str(r["tax_rate_snapshot"])),
                    valve_discount_snapshot=Decimal(str(r["valve_discount_snapshot"])),
                    integrity_hash=str(r["integrity_hash"]),
                    integrity_schema_version=int(r["integrity_schema_version"]),
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
                created_by,
                reason,
                tax_rate_snapshot,
                valve_discount_snapshot,
                integrity_hash,
                integrity_schema_version,
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
            created_by=str(r["created_by"]) if r["created_by"] is not None else None,
            reason=str(r["reason"]) if r["reason"] is not None else None,
            tax_rate_snapshot=Decimal(str(r["tax_rate_snapshot"])),
            valve_discount_snapshot=Decimal(str(r["valve_discount_snapshot"])),
            integrity_hash=str(r["integrity_hash"]),
            integrity_schema_version=int(r["integrity_schema_version"]),
            created_at=str(r["created_at"]),
        )

    def list_version_lines(self, *, version_id: str) -> tuple[TakeoffVersionLineSnapshot, ...]:
        rows = self.conn.execute(
            """
            SELECT
                version_line_id,
                version_id,
                item_code,
                mapping_id,
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
                item_code,
                version_line_id
            """,
            (version_id,),
        ).fetchall()

        out: list[TakeoffVersionLineSnapshot] = []
        for r in rows:
            out.append(
                TakeoffVersionLineSnapshot(
                    version_line_id=str(r["version_line_id"]),
                    version_id=str(r["version_id"]),
                    item_code=str(r["item_code"]),
                    mapping_id=str(r["mapping_id"]) if r["mapping_id"] is not None else None,
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

    # -------------------------
    # Integrity verification
    # -------------------------

    def verify_version_integrity(self, *, version_id: str) -> tuple[bool, str, str]:
        """Recalculate the integrity hash for a version and compare it with the stored one.

        Returns:
            (is_valid, expected_hash, actual_hash)
        """

        version = self.get_version(version_id=version_id)

        if version.integrity_schema_version >= 3:
            raw_rows = self.conn.execute(
                """
                SELECT
                    version_line_id,
                    item_code,
                    mapping_id,
                    qty,
                    notes,
                    description_snapshot,
                    details_snapshot,
                    unit_price_snapshot,
                    taxable_snapshot,
                    COALESCE(stage, 'final') AS stage,
                    COALESCE(factor, '1.0') AS factor,
                    COALESCE(sort_order, 0) AS sort_order
                FROM takeoff_version_lines
                WHERE version_id = ?
                """,
                (version_id,),
            ).fetchall()

            rows = [
                {
                    "version_line_id": str(r["version_line_id"]),
                    "item_code": str(r["item_code"]),
                    "mapping_id": str(r["mapping_id"]) if r["mapping_id"] is not None else None,
                    "qty": str(r["qty"]),
                    "notes": str(r["notes"]) if r["notes"] is not None else None,
                    "description_snapshot": str(r["description_snapshot"]),
                    "details_snapshot": str(r["details_snapshot"]) if r["details_snapshot"] is not None else None,
                    "unit_price_snapshot": str(r["unit_price_snapshot"]),
                    "taxable_snapshot": str(int(r["taxable_snapshot"])),
                    "stage": str(r["stage"] or "final"),
                    "factor": str(r["factor"] or "1.0"),
                    "sort_order": str(int(r["sort_order"] or 0)),
                }
                for r in raw_rows
            ]
        else:
            raw_rows = self.conn.execute(
                """
                SELECT
                    item_code,
                    qty,
                    unit_price_snapshot,
                    taxable_snapshot,
                    COALESCE(stage, 'final') AS stage,
                    COALESCE(factor, '1.0') AS factor,
                    COALESCE(sort_order, 0) AS sort_order
                FROM takeoff_version_lines
                WHERE version_id = ?
                """,
                (version_id,),
            ).fetchall()

            rows = [
                {
                    "item_code": str(r["item_code"]),
                    "qty": str(r["qty"]),
                    "unit_price_snapshot": str(r["unit_price_snapshot"]),
                    "taxable_snapshot": str(int(r["taxable_snapshot"])),
                    "stage": str(r["stage"] or "final"),
                    "factor": str(r["factor"] or "1.0"),
                    "sort_order": str(int(r["sort_order"] or 0)),
                }
                for r in raw_rows
            ]

        actual_hash = self._build_integrity_hash(
            takeoff_id=version.takeoff_id,
            project_code_snapshot=version.project_code_snapshot,
            template_code_snapshot=version.template_code_snapshot,
            tax_rate_snapshot=version.tax_rate_snapshot,
            valve_discount_snapshot=version.valve_discount_snapshot,
            rows=rows,
        )
        expected_hash = version.integrity_hash

        return (actual_hash == expected_hash, expected_hash, actual_hash)
