from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.cli import main
from app.domain.fixture_mapping import (
    FixtureQuantityRef,
    FixtureQuantitySourceKind,
    TemplateFixtureMappingRule,
)
from app.domain.item import Item
from app.domain.project import Project
from app.domain.stage import Stage
from app.domain.template import Template
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_takeoff_line_repository import SqliteTakeoffLineRepository
from app.infrastructure.sqlite_takeoff_repository import SqliteTakeoffRepository
from app.infrastructure.sqlite_template_fixture_mapping_repository import (
    SqliteTemplateFixtureMappingRepository,
)
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository


def _seed_generation_inputs(db_path: Path) -> None:
    conn = SqliteDb(path=db_path).connect()
    try:
        SqliteProjectRepository(conn=conn).upsert(
            Project(
                code="PROJ-001",
                name="Palm Glades",
                contractor="Lennar",
                foreman="JOE",
                is_active=True,
                valve_discount=Decimal("-112.99"),
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
                code="MAT_PER_FIXTURE",
                item_number="MAT_PER_FIXTURE",
                description="Material Per Fixture",
                details="Std",
                unit_price=Decimal("10.00"),
                taxable=True,
                is_active=True,
            )
        )
        SqliteTemplateFixtureMappingRepository(conn=conn).add(
            TemplateFixtureMappingRule(
                mapping_id="map-water-points-ground",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="MAT_PER_FIXTURE",
                stage=Stage.GROUND,
                factor=Decimal("0.30"),
                sort_order=10,
            )
        )
    finally:
        conn.close()


def test_cli_generate_takeoff_from_plan_smoke(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db_path = tmp_path / "takeoff.db"
    _seed_generation_inputs(db_path)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "takeoffs",
            "generate-from-plan",
            "--project",
            "PROJ-001",
            "--template",
            "TH_DEFAULT",
            "--stories",
            "2",
            "--kitchens",
            "1",
            "--garbage-disposals",
            "1",
            "--laundry-rooms",
            "1",
            "--lav-faucets",
            "4",
            "--toilets",
            "3",
            "--showers",
            "2",
            "--bathtubs",
            "1",
            "--half-baths",
            "1",
            "--double-bowl-vanities",
            "1",
            "--hose-bibbs",
            "2",
            "--ice-makers",
            "1",
            "--water-heater-tank-qty",
            "0",
            "--water-heater-tankless-qty",
            "2",
            "--sewer-distance-lf",
            "40",
            "--water-distance-lf",
            "25",
        ]
    )

    captured = capsys.readouterr().out
    assert rc == 0
    assert "TAKEOFF generated id=" in captured

    conn = SqliteDb(path=db_path).connect()
    try:
        takeoffs = SqliteTakeoffRepository(conn=conn).list_for_project("PROJ-001")
        assert len(takeoffs) == 1
        lines = SqliteTakeoffLineRepository(conn=conn).list_for_takeoff(takeoffs[0].takeoff_id)
        assert len(lines) == 1
        assert lines[0].mapping_id == "map-water-points-ground"
        assert lines[0].qty == Decimal("10")
    finally:
        conn.close()


def test_cli_generate_takeoff_from_plan_rejects_negative_counts(tmp_path: Path) -> None:
    db_path = tmp_path / "takeoff.db"

    with pytest.raises(SystemExit):
        main(
            [
                "--db-path",
                str(db_path),
                "takeoffs",
                "generate-from-plan",
                "--project",
                "PROJ-001",
                "--template",
                "TH_DEFAULT",
                "--stories",
                "-1",
                "--kitchens",
                "1",
                "--garbage-disposals",
                "1",
                "--laundry-rooms",
                "1",
                "--lav-faucets",
                "4",
                "--toilets",
                "3",
                "--showers",
                "2",
                "--bathtubs",
                "1",
                "--half-baths",
                "1",
                "--double-bowl-vanities",
                "1",
                "--hose-bibbs",
                "2",
                "--ice-makers",
                "1",
                "--water-heater-tank-qty",
                "0",
                "--water-heater-tankless-qty",
                "2",
                "--sewer-distance-lf",
                "40",
                "--water-distance-lf",
                "25",
            ]
        )
