from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.cli import main
from app.domain.fixture_mapping import (
    FixtureQuantityRef,
    FixtureQuantitySourceKind,
    TemplateFixtureMappingRule,
)
from app.domain.item import Item
from app.domain.project import Project
from app.domain.template import Template
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_template_fixture_mapping_repository import (
    SqliteTemplateFixtureMappingRepository,
)
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository


def _seed_project_override_inputs(db_path: Path) -> None:
    conn = SqliteDb(path=db_path).connect()
    try:
        SqliteProjectRepository(conn=conn).upsert(
            Project(
                code="PROJ-001",
                name="Palm Glades",
                contractor="Lennar",
                foreman="JOE",
                is_active=True,
                valve_discount=Decimal("0.00"),
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
        SqliteItemRepository(conn=conn).upsert(
            Item(
                code="ITEM_001",
                item_number="ITEM_001",
                description="Fixture A",
                details=None,
                unit_price=Decimal("10.00"),
                taxable=True,
                is_active=True,
            )
        )
        SqliteItemRepository(conn=conn).upsert(
            Item(
                code="ITEM_002",
                item_number="ITEM_002",
                description="Fixture B",
                details=None,
                unit_price=Decimal("12.00"),
                taxable=True,
                is_active=True,
            )
        )
        SqliteTemplateFixtureMappingRepository(conn=conn).add(
            TemplateFixtureMappingRule(
                mapping_id="map-001",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM_001",
            )
        )
    finally:
        conn.close()


def test_cli_project_overrides_set_show_list_delete(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "takeoff.db"
    _seed_project_override_inputs(db_path)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "project-overrides",
            "set",
            "--project",
            "PROJ-001",
            "--mapping-id",
            "map-001",
            "--item",
            "ITEM_002",
            "--notes",
            "Use alternate fixture",
        ]
    )
    assert rc == 0

    rc = main(
        [
            "--db-path",
            str(db_path),
            "project-overrides",
            "show",
            "--project",
            "PROJ-001",
            "--mapping-id",
            "map-001",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert "mapping_id=map-001" in output
    assert "item=ITEM_002" in output
    assert "Use alternate fixture" in output

    rc = main(
        [
            "--db-path",
            str(db_path),
            "project-overrides",
            "list",
            "--project",
            "PROJ-001",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert "mapping_id=map-001" in output

    rc = main(
        [
            "--db-path",
            str(db_path),
            "project-overrides",
            "set",
            "--project",
            "PROJ-001",
            "--mapping-id",
            "map-001",
            "--disable",
            "--clear-item",
            "--clear-notes",
        ]
    )
    assert rc == 0

    rc = main(
        [
            "--db-path",
            str(db_path),
            "project-overrides",
            "show",
            "--project",
            "PROJ-001",
            "--mapping-id",
            "map-001",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert "disabled=True" in output
    assert "item=None" in output
    assert "notes=None" in output

    rc = main(
        [
            "--db-path",
            str(db_path),
            "project-overrides",
            "delete",
            "--project",
            "PROJ-001",
            "--mapping-id",
            "map-001",
        ]
    )
    assert rc == 0
    _ = capsys.readouterr()

    rc = main(
        [
            "--db-path",
            str(db_path),
            "project-overrides",
            "list",
            "--project",
            "PROJ-001",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert "mapping_id=map-001" not in output
