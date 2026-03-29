from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.application.errors import InvalidInputError
from app.domain.fixture_mapping import (
    FixtureQuantityRef,
    FixtureQuantitySourceKind,
    ProjectFixtureOverride,
    TemplateFixtureMappingRule,
)
from app.domain.item import Item
from app.domain.project import Project
from app.domain.stage import Stage
from app.domain.template import Template
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_project_fixture_override_repository import (
    SqliteProjectFixtureOverrideRepository,
)
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_template_fixture_mapping_repository import (
    SqliteTemplateFixtureMappingRepository,
)
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository


def _make_conn(tmp_path: Path):
    return SqliteDb(path=tmp_path / "test_takeoff.db").connect()


def _seed_item(conn, code: str = "ITEM-001") -> None:
    SqliteItemRepository(conn=conn).upsert(
        Item(
            code=code,
            item_number=code,
            description=f"Item {code}",
            details=None,
            unit_price=Decimal("10.00"),
            taxable=True,
            is_active=True,
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


def _seed_project(conn, code: str = "PROJ-001") -> None:
    SqliteProjectRepository(conn=conn).upsert(
        Project(
            code=code,
            name="Palm Glades",
            contractor="Lennar",
            foreman="JOE",
            is_active=True,
        )
    )


def test_template_fixture_mapping_repository_add_get_list(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_item(conn, "ITEM-001")
        _seed_item(conn, "ITEM-002")
        _seed_template(conn, "TH_DEFAULT")

        repo = SqliteTemplateFixtureMappingRepository(conn=conn)
        repo.add(
            TemplateFixtureMappingRule(
                mapping_id="map-001",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM-001",
                qty_multiplier=Decimal("1.0"),
                stage=Stage.GROUND,
                factor=Decimal("0.30"),
                sort_order=20,
                notes="Ground split",
                is_active=True,
            )
        )
        repo.add(
            TemplateFixtureMappingRule(
                mapping_id="map-002",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.CONSTANT,
                    constant_qty=Decimal("1"),
                ),
                item_code="ITEM-002",
                qty_multiplier=Decimal("1.0"),
                stage=Stage.FINAL,
                factor=Decimal("1.0"),
                sort_order=10,
                notes=None,
                is_active=False,
            )
        )

        rule = repo.get("map-001")
        assert rule.mapping_id == "map-001"
        assert rule.template_code == "TH_DEFAULT"
        assert rule.quantity_ref.source_kind == FixtureQuantitySourceKind.DERIVED
        assert rule.quantity_ref.source_name == "water_points"
        assert rule.item_code == "ITEM-001"
        assert rule.stage == Stage.GROUND
        assert rule.factor == Decimal("0.30")
        assert rule.sort_order == 20
        assert rule.notes == "Ground split"
        assert rule.is_active is True

        active_rules = repo.list_for_template("TH_DEFAULT", include_inactive=False)
        assert [r.mapping_id for r in active_rules] == ["map-001"]

        all_rules = repo.list_for_template("TH_DEFAULT", include_inactive=True)
        assert [r.mapping_id for r in all_rules] == ["map-002", "map-001"]
        assert all_rules[0].quantity_ref.source_kind == FixtureQuantitySourceKind.CONSTANT
        assert all_rules[0].quantity_ref.constant_qty == Decimal("1")
        assert all_rules[0].is_active is False

    finally:
        conn.close()


def test_template_fixture_mapping_repository_fk_validation(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        repo = SqliteTemplateFixtureMappingRepository(conn=conn)

        with pytest.raises(InvalidInputError):
            repo.add(
                TemplateFixtureMappingRule(
                    mapping_id="map-missing-template",
                    template_code="MISSING_TEMPLATE",
                    quantity_ref=FixtureQuantityRef(
                        source_kind=FixtureQuantitySourceKind.DERIVED,
                        source_name="water_points",
                    ),
                    item_code="ITEM-001",
                    stage=Stage.GROUND,
                )
            )

        _seed_template(conn, "TH_DEFAULT")
        with pytest.raises(InvalidInputError):
            repo.add(
                TemplateFixtureMappingRule(
                    mapping_id="map-missing-item",
                    template_code="TH_DEFAULT",
                    quantity_ref=FixtureQuantityRef(
                        source_kind=FixtureQuantitySourceKind.DERIVED,
                        source_name="water_points",
                    ),
                    item_code="ITEM-NOT-FOUND",
                    stage=Stage.GROUND,
                )
            )

    finally:
        conn.close()


def test_template_fixture_mapping_repository_enforces_unique_mapping_id(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_item(conn, "ITEM-001")
        _seed_item(conn, "ITEM-002")
        _seed_template(conn, "TH_DEFAULT")
        repo = SqliteTemplateFixtureMappingRepository(conn=conn)

        repo.add(
            TemplateFixtureMappingRule(
                mapping_id="stable-map-id",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM-001",
                stage=Stage.GROUND,
            )
        )

        with pytest.raises(InvalidInputError):
            repo.add(
                TemplateFixtureMappingRule(
                    mapping_id="stable-map-id",
                    template_code="TH_DEFAULT",
                    quantity_ref=FixtureQuantityRef(
                        source_kind=FixtureQuantitySourceKind.CONSTANT,
                        constant_qty=Decimal("1"),
                    ),
                    item_code="ITEM-002",
                    stage=Stage.FINAL,
                )
            )

    finally:
        conn.close()


def test_template_fixture_mapping_repository_upsert_preserves_mapping_id_and_updates_fields(
    tmp_path: Path,
) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_item(conn, "ITEM-001")
        _seed_item(conn, "ITEM-002")
        _seed_template(conn, "TH_DEFAULT")
        repo = SqliteTemplateFixtureMappingRepository(conn=conn)

        repo.add(
            TemplateFixtureMappingRule(
                mapping_id="map-stable",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM-001",
                stage=Stage.GROUND,
                factor=Decimal("0.30"),
                sort_order=10,
                notes="Original",
            )
        )

        repo.upsert(
            TemplateFixtureMappingRule(
                mapping_id="map-stable",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.CONSTANT,
                    constant_qty=Decimal("2"),
                ),
                item_code="ITEM-002",
                stage=Stage.FINAL,
                factor=Decimal("1.0"),
                sort_order=25,
                notes="Updated",
            )
        )

        rule = repo.get("map-stable")
        assert rule.mapping_id == "map-stable"
        assert rule.quantity_ref.source_kind == FixtureQuantitySourceKind.CONSTANT
        assert rule.quantity_ref.constant_qty == Decimal("2")
        assert rule.quantity_ref.source_name is None
        assert rule.item_code == "ITEM-002"
        assert rule.stage == Stage.FINAL
        assert rule.sort_order == 25
        assert rule.notes == "Updated"
    finally:
        conn.close()


def test_template_fixture_mapping_repository_can_activate_and_deactivate(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_item(conn, "ITEM-001")
        _seed_template(conn, "TH_DEFAULT")
        repo = SqliteTemplateFixtureMappingRepository(conn=conn)

        repo.add(
            TemplateFixtureMappingRule(
                mapping_id="map-active-toggle",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM-001",
                stage=Stage.GROUND,
            )
        )

        repo.set_active("map-active-toggle", is_active=False)
        assert repo.get("map-active-toggle").is_active is False
        assert repo.list_for_template("TH_DEFAULT") == ()

        repo.set_active("map-active-toggle", is_active=True)
        assert repo.get("map-active-toggle").is_active is True
        assert [r.mapping_id for r in repo.list_for_template("TH_DEFAULT")] == ["map-active-toggle"]
    finally:
        conn.close()


def test_project_fixture_override_repository_add_get_list(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_item(conn, "ITEM-001")
        _seed_item(conn, "ITEM-OVERRIDE")
        _seed_template(conn, "TH_DEFAULT")
        _seed_project(conn, "PROJ-001")

        mapping_repo = SqliteTemplateFixtureMappingRepository(conn=conn)
        mapping_repo.add(
            TemplateFixtureMappingRule(
                mapping_id="map-001",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM-001",
                stage=Stage.GROUND,
            )
        )

        repo = SqliteProjectFixtureOverrideRepository(conn=conn)
        repo.add(
            ProjectFixtureOverride(
                project_code="PROJ-001",
                mapping_id="map-001",
                is_disabled=False,
                item_code_override="ITEM-OVERRIDE",
                notes_override="Use alternate fixture",
            )
        )

        override = repo.get(project_code="PROJ-001", mapping_id="map-001")
        assert override.project_code == "PROJ-001"
        assert override.mapping_id == "map-001"
        assert override.is_disabled is False
        assert override.item_code_override == "ITEM-OVERRIDE"
        assert override.notes_override == "Use alternate fixture"

        rows = repo.list_for_project("PROJ-001")
        assert len(rows) == 1
        assert rows[0] == override

    finally:
        conn.close()


def test_project_fixture_override_repository_fk_validation(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        repo = SqliteProjectFixtureOverrideRepository(conn=conn)

        with pytest.raises(InvalidInputError):
            repo.add(
                ProjectFixtureOverride(
                    project_code="MISSING_PROJECT",
                    mapping_id="missing-map",
                )
            )

        _seed_item(conn, "ITEM-001")
        _seed_template(conn, "TH_DEFAULT")
        _seed_project(conn, "PROJ-001")
        SqliteTemplateFixtureMappingRepository(conn=conn).add(
            TemplateFixtureMappingRule(
                mapping_id="map-001",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM-001",
                stage=Stage.GROUND,
            )
        )

        with pytest.raises(InvalidInputError):
            repo.add(
                ProjectFixtureOverride(
                    project_code="PROJ-001",
                    mapping_id="missing-map",
                )
            )

        with pytest.raises(InvalidInputError):
            repo.add(
                ProjectFixtureOverride(
                    project_code="PROJ-001",
                    mapping_id="map-001",
                    item_code_override="ITEM-NOT-FOUND",
                )
            )

    finally:
        conn.close()


def test_project_fixture_override_repository_enforces_unique_project_mapping_pair(
    tmp_path: Path,
) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_item(conn, "ITEM-001")
        _seed_template(conn, "TH_DEFAULT")
        _seed_project(conn, "PROJ-001")

        SqliteTemplateFixtureMappingRepository(conn=conn).add(
            TemplateFixtureMappingRule(
                mapping_id="map-001",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM-001",
                stage=Stage.GROUND,
            )
        )

        repo = SqliteProjectFixtureOverrideRepository(conn=conn)
        repo.add(
            ProjectFixtureOverride(
                project_code="PROJ-001",
                mapping_id="map-001",
                notes_override="First override",
            )
        )

        with pytest.raises(InvalidInputError):
            repo.add(
                ProjectFixtureOverride(
                    project_code="PROJ-001",
                    mapping_id="map-001",
                    notes_override="Duplicate override",
                )
            )

    finally:
        conn.close()


def test_project_fixture_override_repository_upsert_updates_existing_pair(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_item(conn, "ITEM-001")
        _seed_item(conn, "ITEM-002")
        _seed_template(conn, "TH_DEFAULT")
        _seed_project(conn, "PROJ-001")

        SqliteTemplateFixtureMappingRepository(conn=conn).add(
            TemplateFixtureMappingRule(
                mapping_id="map-001",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM-001",
                stage=Stage.GROUND,
            )
        )

        repo = SqliteProjectFixtureOverrideRepository(conn=conn)
        repo.add(
            ProjectFixtureOverride(
                project_code="PROJ-001",
                mapping_id="map-001",
                notes_override="First",
            )
        )
        repo.upsert(
            ProjectFixtureOverride(
                project_code="PROJ-001",
                mapping_id="map-001",
                is_disabled=True,
                item_code_override=None,
                notes_override="Updated",
            )
        )

        override = repo.get(project_code="PROJ-001", mapping_id="map-001")
        assert override.is_disabled is True
        assert override.notes_override == "Updated"
    finally:
        conn.close()


def test_project_fixture_override_repository_delete_removes_override(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        _seed_item(conn, "ITEM-001")
        _seed_template(conn, "TH_DEFAULT")
        _seed_project(conn, "PROJ-001")

        SqliteTemplateFixtureMappingRepository(conn=conn).add(
            TemplateFixtureMappingRule(
                mapping_id="map-001",
                template_code="TH_DEFAULT",
                quantity_ref=FixtureQuantityRef(
                    source_kind=FixtureQuantitySourceKind.DERIVED,
                    source_name="water_points",
                ),
                item_code="ITEM-001",
                stage=Stage.GROUND,
            )
        )

        repo = SqliteProjectFixtureOverrideRepository(conn=conn)
        repo.add(
            ProjectFixtureOverride(
                project_code="PROJ-001",
                mapping_id="map-001",
                notes_override="To be removed",
            )
        )

        repo.delete(project_code="PROJ-001", mapping_id="map-001")
        assert repo.list_for_project("PROJ-001") == ()
    finally:
        conn.close()
