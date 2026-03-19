from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.domain.item import Item
from app.domain.project import Project
from app.domain.stage import Stage
from app.domain.takeoff_line_snapshot import TakeoffLineSnapshot
from app.domain.takeoff_record import TakeoffRecord
from app.domain.template import Template
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_takeoff_line_repository import SqliteTakeoffLineRepository
from app.infrastructure.sqlite_takeoff_repository import SqliteTakeoffRepository
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository


def _make_conn(tmp_path: Path):
    return SqliteDb(path=tmp_path / "test_takeoff.db").connect()


def _seed_catalog(conn) -> None:
    SqliteItemRepository(conn=conn).upsert(
        Item(
            code="ITEM-001",
            item_number="ITEM-001",
            description="Fixture",
            details="Std",
            unit_price=Decimal("100.00"),
            taxable=True,
            is_active=True,
        )
    )
    SqliteProjectRepository(conn=conn).upsert(
        Project(
            code="PROJ-001",
            name="Palm Glades",
            contractor="Lennar",
            foreman="JOE",
            is_active=True,
        )
    )
    SqliteTemplateRepository(conn=conn).upsert(
        Template(
            code="TH_DEFAULT",
            name="Townhomes Default",
            category="TH",
            is_active=True,
        )
    )


def _seed_takeoff(conn) -> str:
    takeoff_id = "takeoff-001"
    SqliteTakeoffRepository(conn=conn).create(
        TakeoffRecord(
            takeoff_id=takeoff_id,
            project_code="PROJ-001",
            template_code="TH_DEFAULT",
            tax_rate=Decimal("0.07"),
            valve_discount=Decimal("0.00"),
        )
    )
    return takeoff_id


def test_live_takeoff_lines_support_duplicate_item_code_across_stages(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_catalog(conn)
        takeoff_id = _seed_takeoff(conn)
        repo = SqliteTakeoffLineRepository(conn=conn)

        repo.add_line(
            TakeoffLineSnapshot(
                takeoff_id=takeoff_id,
                item_code="ITEM-001",
                qty=Decimal("10"),
                notes="Ground line",
                description_snapshot="Fixture",
                details_snapshot="Std",
                unit_price_snapshot=Decimal("100.00"),
                taxable_snapshot=True,
                stage=Stage.GROUND,
                factor=Decimal("0.30"),
                sort_order=10,
                line_id="line-ground",
                mapping_id="map-ground",
            )
        )
        repo.add_line(
            TakeoffLineSnapshot(
                takeoff_id=takeoff_id,
                item_code="ITEM-001",
                qty=Decimal("10"),
                notes="Final line",
                description_snapshot="Fixture",
                details_snapshot="Std",
                unit_price_snapshot=Decimal("100.00"),
                taxable_snapshot=True,
                stage=Stage.FINAL,
                factor=Decimal("0.40"),
                sort_order=20,
                line_id="line-final",
                mapping_id="map-final",
            )
        )

        lines = repo.list_for_takeoff(takeoff_id)
        assert len(lines) == 2
        assert [ln.line_id for ln in lines] == ["line-ground", "line-final"]
        assert [ln.item_code for ln in lines] == ["ITEM-001", "ITEM-001"]
        assert [ln.mapping_id for ln in lines] == ["map-ground", "map-final"]

        repo.update_line(line_id="line-ground", qty=Decimal("12"))
        updated = repo.list_for_takeoff(takeoff_id)
        assert updated[0].qty == Decimal("12")
        assert updated[1].qty == Decimal("10")

        repo.delete_line(line_id="line-final")
        remaining = repo.list_for_takeoff(takeoff_id)
        assert len(remaining) == 1
        assert remaining[0].line_id == "line-ground"
        assert remaining[0].mapping_id == "map-ground"

    finally:
        conn.close()


def test_snapshot_version_preserves_duplicate_item_codes_and_mapping_ids(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_catalog(conn)
        takeoff_id = _seed_takeoff(conn)
        takeoff_lines = SqliteTakeoffLineRepository(conn=conn)
        takeoffs = SqliteTakeoffRepository(conn=conn)

        takeoff_lines.bulk_insert(
            [
                TakeoffLineSnapshot(
                    takeoff_id=takeoff_id,
                    item_code="ITEM-001",
                    qty=Decimal("10"),
                    notes="Ground line",
                    description_snapshot="Fixture",
                    details_snapshot="Std",
                    unit_price_snapshot=Decimal("100.00"),
                    taxable_snapshot=True,
                    stage=Stage.GROUND,
                    factor=Decimal("0.30"),
                    sort_order=10,
                    line_id="line-ground",
                    mapping_id="map-ground",
                ),
                TakeoffLineSnapshot(
                    takeoff_id=takeoff_id,
                    item_code="ITEM-001",
                    qty=Decimal("10"),
                    notes="Final line",
                    description_snapshot="Fixture",
                    details_snapshot="Std",
                    unit_price_snapshot=Decimal("100.00"),
                    taxable_snapshot=True,
                    stage=Stage.FINAL,
                    factor=Decimal("0.40"),
                    sort_order=20,
                    line_id="line-final",
                    mapping_id="map-final",
                ),
            ]
        )

        version_id = takeoffs.create_snapshot_version(
            takeoff_id=takeoff_id,
            created_by="tester",
            reason="duplicate item snapshot",
        )

        version_lines = takeoffs.list_version_lines(version_id=version_id)
        assert len(version_lines) == 2
        assert [ln.item_code for ln in version_lines] == ["ITEM-001", "ITEM-001"]
        assert [ln.mapping_id for ln in version_lines] == ["map-ground", "map-final"]
        assert all(ln.version_line_id for ln in version_lines)
        assert [ln.stage for ln in version_lines] == ["ground", "final"]

        ok, expected_hash, actual_hash = takeoffs.verify_version_integrity(version_id=version_id)
        assert ok is True
        assert expected_hash == actual_hash

    finally:
        conn.close()
