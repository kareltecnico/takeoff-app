from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.cli import main
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


def _seed_takeoff_with_duplicate_lines(
    db_path: Path,
    *,
    project_active: bool = True,
) -> str:
    conn = SqliteDb(path=db_path).connect()
    try:
        SqliteItemRepository(conn=conn).upsert(
            Item(
                code="ITEM_001",
                item_number="ITEM_001",
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
                is_active=project_active,
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
        takeoff_id = "takeoff-001"
        SqliteTakeoffRepository(conn=conn).create(
            TakeoffRecord(
                takeoff_id=takeoff_id,
                project_code="PROJ-001",
                template_code="TH_DEFAULT",
                tax_rate=Decimal("0.07"),
            )
        )
        SqliteTakeoffLineRepository(conn=conn).bulk_insert(
            [
                TakeoffLineSnapshot(
                    takeoff_id=takeoff_id,
                    item_code="ITEM_001",
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
                    item_code="ITEM_001",
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
        return takeoff_id
    finally:
        conn.close()


def test_cli_takeoff_lines_lists_line_id_and_mapping_id(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "takeoff.db"
    takeoff_id = _seed_takeoff_with_duplicate_lines(db_path)

    rc = main(["--db-path", str(db_path), "takeoffs", "lines", "--id", takeoff_id])
    output = capsys.readouterr().out
    assert rc == 0
    assert "line_id=line-ground" in output
    assert "mapping_id=map-ground" in output
    assert "item_code=ITEM_001" in output
    assert "qty=10" in output
    assert "stage=ground" in output
    assert "factor=0.30" in output
    assert "sort_order=10" in output
    assert "description=Fixture" in output
    assert "line_id=line-final" in output
    assert "mapping_id=map-final" in output


def test_cli_update_line_by_line_id_targets_only_selected_duplicate(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "takeoff.db"
    takeoff_id = _seed_takeoff_with_duplicate_lines(db_path)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "takeoffs",
            "update-line",
            "--id",
            takeoff_id,
            "--line-id",
            "line-ground",
            "--qty",
            "12",
        ]
    )
    assert rc == 0
    _ = capsys.readouterr()

    conn = SqliteDb(path=db_path).connect()
    try:
        lines = SqliteTakeoffLineRepository(conn=conn).list_for_takeoff(takeoff_id)
        assert [ln.line_id for ln in lines] == ["line-ground", "line-final"]
        assert lines[0].qty == Decimal("12")
        assert lines[1].qty == Decimal("10")
    finally:
        conn.close()


def test_cli_delete_line_by_line_id_targets_only_selected_duplicate(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "takeoff.db"
    takeoff_id = _seed_takeoff_with_duplicate_lines(db_path)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "takeoffs",
            "delete-line",
            "--id",
            takeoff_id,
            "--line-id",
            "line-final",
        ]
    )
    assert rc == 0
    _ = capsys.readouterr()

    conn = SqliteDb(path=db_path).connect()
    try:
        lines = SqliteTakeoffLineRepository(conn=conn).list_for_takeoff(takeoff_id)
        assert len(lines) == 1
        assert lines[0].line_id == "line-ground"
        assert lines[0].mapping_id == "map-ground"
    finally:
        conn.close()


def test_cli_update_line_rejects_ambiguous_item_targeting(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "takeoff.db"
    takeoff_id = _seed_takeoff_with_duplicate_lines(db_path)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "takeoffs",
            "update-line",
            "--id",
            takeoff_id,
            "--item",
            "ITEM_001",
            "--qty",
            "12",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 2
    assert f"takeoffs lines --id {takeoff_id}" in output
    assert "--line-id" in output


def test_cli_delete_line_rejects_ambiguous_item_targeting(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "takeoff.db"
    takeoff_id = _seed_takeoff_with_duplicate_lines(db_path)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "takeoffs",
            "delete-line",
            "--id",
            takeoff_id,
            "--item",
            "ITEM_001",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 2
    assert f"takeoffs lines --id {takeoff_id}" in output
    assert "--line-id" in output


def test_cli_current_line_editing_rejects_closed_projects(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "takeoff.db"
    takeoff_id = _seed_takeoff_with_duplicate_lines(db_path, project_active=False)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "takeoffs",
            "update-line",
            "--id",
            takeoff_id,
            "--line-id",
            "line-ground",
            "--qty",
            "12",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 2
    assert "Project is closed" in output

    rc = main(
        [
            "--db-path",
            str(db_path),
            "takeoffs",
            "delete-line",
            "--id",
            takeoff_id,
            "--line-id",
            "line-final",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 2
    assert "Project is closed" in output
