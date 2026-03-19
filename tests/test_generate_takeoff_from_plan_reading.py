from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.application.errors import InvalidInputError
from app.application.generate_takeoff_from_plan_reading import (
    GenerateTakeoffFromPlanReading,
)
from app.domain.fixture_mapping import (
    FixtureQuantityRef,
    FixtureQuantitySourceKind,
    ProjectFixtureOverride,
    TemplateFixtureMappingRule,
)
from app.domain.item import Item
from app.domain.plan_reading_input import PlanReadingInput
from app.domain.project import Project
from app.domain.stage import Stage
from app.domain.template import Template
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_project_fixture_override_repository import (
    SqliteProjectFixtureOverrideRepository,
)
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_takeoff_line_repository import SqliteTakeoffLineRepository
from app.infrastructure.sqlite_takeoff_repository import SqliteTakeoffRepository
from app.infrastructure.sqlite_template_fixture_mapping_repository import (
    SqliteTemplateFixtureMappingRepository,
)
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository


def _make_conn(tmp_path: Path):
    return SqliteDb(path=tmp_path / "test_takeoff.db").connect()


def _plan(*, ice_makers: int = 1) -> PlanReadingInput:
    return PlanReadingInput(
        stories=2,
        kitchens=1,
        garbage_disposals=1,
        laundry_rooms=1,
        lav_faucets=4,
        toilets=3,
        showers=2,
        bathtubs=1,
        half_baths=1,
        double_bowl_vanities=1,
        hose_bibbs=2,
        ice_makers=ice_makers,
        water_heater_tank_qty=0,
        water_heater_tankless_qty=2,
        sewer_distance_lf=40.0,
        water_distance_lf=25.0,
    )


def _seed_project(conn, code: str = "PROJ-001") -> None:
    SqliteProjectRepository(conn=conn).upsert(
        Project(
            code=code,
            name="Palm Glades",
            contractor="Lennar",
            foreman="JOE",
            is_active=True,
            valve_discount=Decimal("-112.99"),
        )
    )


def _seed_template(conn, code: str = "TH_DEFAULT") -> None:
    SqliteTemplateRepository(conn=conn).upsert(
        Template(
            code=code,
            name="Townhomes Default",
            category="TH",
            is_active=True,
        )
    )


def _seed_item(
    conn,
    *,
    code: str,
    description: str,
    unit_price: str = "10.00",
    taxable: bool = True,
) -> None:
    SqliteItemRepository(conn=conn).upsert(
        Item(
            code=code,
            item_number=code,
            description=description,
            details=f"{description} Details",
            unit_price=Decimal(unit_price),
            taxable=taxable,
            is_active=True,
        )
    )


def _build_use_case(conn) -> GenerateTakeoffFromPlanReading:
    return GenerateTakeoffFromPlanReading(
        project_repo=SqliteProjectRepository(conn=conn),
        template_repo=SqliteTemplateRepository(conn=conn),
        template_fixture_mapping_repo=SqliteTemplateFixtureMappingRepository(conn=conn),
        project_fixture_override_repo=SqliteProjectFixtureOverrideRepository(conn=conn),
        item_repo=SqliteItemRepository(conn=conn),
        takeoff_repo=SqliteTakeoffRepository(conn=conn),
        takeoff_line_repo=SqliteTakeoffLineRepository(conn=conn),
    )


def test_generate_takeoff_from_plan_reading_persists_current_lines(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_project(conn)
        _seed_template(conn)
        _seed_item(conn, code="MAT_PER_FIXTURE", description="Material Per Fixture")
        _seed_item(conn, code="HOSE_BIBB_STD", description="Hose Bibb")

        mappings = SqliteTemplateFixtureMappingRepository(conn=conn)
        mappings.add(
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
                notes="Ground split",
            )
        )
        mappings.add(
            TemplateFixtureMappingRule(
                mapping_id="map-hose-bibb",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.PLAN,
                    source_name="hose_bibbs",
                ),
                item_code="HOSE_BIBB_STD",
                stage=Stage.TOPOUT,
                factor=Decimal("1.0"),
                sort_order=20,
            )
        )

        use_case = _build_use_case(conn)
        takeoff_id = use_case(
            project_code="PROJ-001",
            template_code="TH_DEFAULT",
            plan=_plan(),
        )

        takeoff = SqliteTakeoffRepository(conn=conn).get(takeoff_id=takeoff_id)
        assert takeoff.project_code == "PROJ-001"
        assert takeoff.template_code == "TH_DEFAULT"
        assert takeoff.tax_rate == Decimal("0.07")
        assert takeoff.valve_discount == Decimal("-112.99")

        lines = SqliteTakeoffLineRepository(conn=conn).list_for_takeoff(takeoff_id)
        assert len(lines) == 2

        assert lines[0].mapping_id == "map-water-points-ground"
        assert lines[0].item_code == "MAT_PER_FIXTURE"
        assert lines[0].qty == Decimal("10")
        assert lines[0].stage == Stage.GROUND
        assert lines[0].factor == Decimal("0.30")
        assert lines[0].sort_order == 10
        assert lines[0].notes == "Ground split"
        assert lines[0].description_snapshot == "Material Per Fixture"

        assert lines[1].mapping_id == "map-hose-bibb"
        assert lines[1].item_code == "HOSE_BIBB_STD"
        assert lines[1].qty == Decimal("2")
        assert lines[1].stage == Stage.TOPOUT
        assert lines[1].factor == Decimal("1.0")
        assert lines[1].sort_order == 20
    finally:
        conn.close()


def test_generate_takeoff_from_plan_reading_applies_item_override(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_project(conn)
        _seed_template(conn)
        _seed_item(conn, code="TANKLESS_STD", description="Standard Tankless")
        _seed_item(conn, code="TANKLESS_RHEEM", description="Rheem Tankless")

        SqliteTemplateFixtureMappingRepository(conn=conn).add(
            TemplateFixtureMappingRule(
                mapping_id="map-tankless-heater",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="install_tankless_water_heater_qty",
                ),
                item_code="TANKLESS_STD",
                stage=Stage.FINAL,
                sort_order=30,
            )
        )
        SqliteProjectFixtureOverrideRepository(conn=conn).add(
            ProjectFixtureOverride(
                project_code="PROJ-001",
                mapping_id="map-tankless-heater",
                item_code_override="TANKLESS_RHEEM",
            )
        )

        takeoff_id = _build_use_case(conn)(
            project_code="PROJ-001",
            template_code="TH_DEFAULT",
            plan=_plan(),
        )

        lines = SqliteTakeoffLineRepository(conn=conn).list_for_takeoff(takeoff_id)
        assert len(lines) == 1
        assert lines[0].mapping_id == "map-tankless-heater"
        assert lines[0].item_code == "TANKLESS_RHEEM"
        assert lines[0].qty == Decimal("2")
        assert lines[0].description_snapshot == "Rheem Tankless"
    finally:
        conn.close()


def test_generate_takeoff_from_plan_reading_skips_disabled_override(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_project(conn)
        _seed_template(conn)
        _seed_item(conn, code="MAT_PER_FIXTURE", description="Material Per Fixture")
        _seed_item(conn, code="HOSE_BIBB_STD", description="Hose Bibb")

        mappings = SqliteTemplateFixtureMappingRepository(conn=conn)
        mappings.add(
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
        mappings.add(
            TemplateFixtureMappingRule(
                mapping_id="map-hose-bibb",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.PLAN,
                    source_name="hose_bibbs",
                ),
                item_code="HOSE_BIBB_STD",
                stage=Stage.TOPOUT,
                sort_order=20,
            )
        )

        SqliteProjectFixtureOverrideRepository(conn=conn).add(
            ProjectFixtureOverride(
                project_code="PROJ-001",
                mapping_id="map-hose-bibb",
                is_disabled=True,
            )
        )

        takeoff_id = _build_use_case(conn)(
            project_code="PROJ-001",
            template_code="TH_DEFAULT",
            plan=_plan(),
        )

        lines = SqliteTakeoffLineRepository(conn=conn).list_for_takeoff(takeoff_id)
        assert len(lines) == 1
        assert lines[0].mapping_id == "map-water-points-ground"
        assert lines[0].item_code == "MAT_PER_FIXTURE"
    finally:
        conn.close()


def test_generate_takeoff_from_plan_reading_rejects_duplicate_takeoff(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_project(conn)
        _seed_template(conn)
        _seed_item(conn, code="MAT_PER_FIXTURE", description="Material Per Fixture")

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
            )
        )

        use_case = _build_use_case(conn)
        _ = use_case(
            project_code="PROJ-001",
            template_code="TH_DEFAULT",
            plan=_plan(),
        )

        with pytest.raises(InvalidInputError, match="Takeoff already exists"):
            use_case(
                project_code="PROJ-001",
                template_code="TH_DEFAULT",
                plan=_plan(),
            )
    finally:
        conn.close()


def test_generate_takeoff_from_plan_reading_fails_when_no_lines_resolve(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_project(conn)
        _seed_template(conn)
        _seed_item(conn, code="ICE_MAKER_STD", description="Ice Maker")

        SqliteTemplateFixtureMappingRepository(conn=conn).add(
            TemplateFixtureMappingRule(
                mapping_id="map-ice-maker",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="install_ice_maker_qty",
                ),
                item_code="ICE_MAKER_STD",
                stage=Stage.TOPOUT,
            )
        )

        with pytest.raises(
            InvalidInputError,
            match="produced no resolved lines",
        ):
            _build_use_case(conn)(
                project_code="PROJ-001",
                template_code="TH_DEFAULT",
                plan=_plan(ice_makers=0),
            )

        assert SqliteTakeoffRepository(conn=conn).list_for_project("PROJ-001") == ()
    finally:
        conn.close()


def test_generated_takeoff_snapshot_preserves_mapping_ids(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_project(conn)
        _seed_template(conn)
        _seed_item(conn, code="MAT_PER_FIXTURE", description="Material Per Fixture")

        mappings = SqliteTemplateFixtureMappingRepository(conn=conn)
        mappings.add(
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
        mappings.add(
            TemplateFixtureMappingRule(
                mapping_id="map-water-points-final",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="MAT_PER_FIXTURE",
                stage=Stage.FINAL,
                factor=Decimal("0.40"),
                sort_order=20,
            )
        )

        takeoff_id = _build_use_case(conn)(
            project_code="PROJ-001",
            template_code="TH_DEFAULT",
            plan=_plan(),
        )

        live_lines = SqliteTakeoffLineRepository(conn=conn).list_for_takeoff(takeoff_id)
        assert [ln.mapping_id for ln in live_lines] == [
            "map-water-points-ground",
            "map-water-points-final",
        ]
        assert [ln.item_code for ln in live_lines] == ["MAT_PER_FIXTURE", "MAT_PER_FIXTURE"]

        takeoffs = SqliteTakeoffRepository(conn=conn)
        version_id = takeoffs.create_snapshot_version(
            takeoff_id=takeoff_id,
            created_by="tester",
            reason="verify mapping continuity",
        )

        version_lines = takeoffs.list_version_lines(version_id=version_id)
        assert [ln.mapping_id for ln in version_lines] == [
            "map-water-points-ground",
            "map-water-points-final",
        ]
        assert [ln.stage for ln in version_lines] == ["ground", "final"]

        ok, expected_hash, actual_hash = takeoffs.verify_version_integrity(version_id=version_id)
        assert ok is True
        assert expected_hash == actual_hash
    finally:
        conn.close()
