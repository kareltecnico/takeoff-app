from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.application.errors import InvalidInputError
from app.application.seed_takeoff_from_template import SeedTakeoffFromTemplate
from app.domain.item import Item
from app.domain.project import Project
from app.domain.template import Template
from app.domain.template_line import TemplateLine
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_takeoff_line_repository import SqliteTakeoffLineRepository
from app.infrastructure.sqlite_takeoff_repository import SqliteTakeoffRepository
from app.infrastructure.sqlite_template_line_repository import SqliteTemplateLineRepository
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository


def _make_conn(tmp_path: Path):
    return SqliteDb(path=tmp_path / "test_takeoff.db").connect()


def test_seed_takeoff_from_template_creates_snapshot(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        items = SqliteItemRepository(conn=conn)
        projects = SqliteProjectRepository(conn=conn)
        templates = SqliteTemplateRepository(conn=conn)
        template_lines = SqliteTemplateLineRepository(conn=conn)

        takeoffs = SqliteTakeoffRepository(conn=conn)
        takeoff_lines = SqliteTakeoffLineRepository(conn=conn)

        items.upsert(
            Item(
                code="ITEM-001",
                item_number="ITEM-001",
                description="Kitchen Faucet",
                details="Chrome",
                unit_price=Decimal("100.00"),
                taxable=True,
                is_active=True,
            )
        )

        projects.upsert(
            Project(
                code="PROJ-001",
                name="Palm Glades",
                contractor="Lennar",
                foreman="JOE",
                is_active=True,
            )
        )

        templates.upsert(
            Template(
                code="TH_DEFAULT",
                name="Townhomes Default",
                category="TH",
                is_active=True,
            )
        )

        template_lines.upsert(
            TemplateLine(
                template_code="TH_DEFAULT",
                item_code="ITEM-001",
                qty=Decimal("2"),
                notes="Default qty",
            )
        )

        use_case = SeedTakeoffFromTemplate(
            project_repo=projects,
            template_repo=templates,
            template_line_repo=template_lines,
            item_repo=items,
            takeoff_repo=takeoffs,
            takeoff_line_repo=takeoff_lines,
        )

        takeoff_id = use_case(
            project_code="PROJ-001", 
            template_code="TH_DEFAULT", 
            tax_rate_override=Decimal("0.07")
        )

        t = takeoffs.get(takeoff_id)
        assert t.project_code == "PROJ-001"
        assert t.template_code == "TH_DEFAULT"
        assert t.tax_rate == Decimal("0.07")

        lines = takeoff_lines.list_for_takeoff(takeoff_id)
        assert len(lines) == 1
        ln = lines[0]
        assert ln.item_code == "ITEM-001"
        assert ln.qty == Decimal("2")
        assert ln.description_snapshot == "Kitchen Faucet"
        assert ln.details_snapshot == "Chrome"
        assert ln.unit_price_snapshot == Decimal("100.00")
        assert ln.taxable_snapshot is True

    finally:
        conn.close()


def test_seed_fails_if_template_has_no_lines(tmp_path: Path) -> None:
    conn = _make_conn(tmp_path)
    try:
        items = SqliteItemRepository(conn=conn)
        projects = SqliteProjectRepository(conn=conn)
        templates = SqliteTemplateRepository(conn=conn)
        template_lines = SqliteTemplateLineRepository(conn=conn)

        takeoffs = SqliteTakeoffRepository(conn=conn)
        takeoff_lines = SqliteTakeoffLineRepository(conn=conn)

        projects.upsert(
            Project(
                code="PROJ-001",
                name="Palm Glades",
                contractor="Lennar",
                foreman="JOE",
                is_active=True,
            )
        )

        templates.upsert(
            Template(
                code="TH_DEFAULT",
                name="Townhomes Default",
                category="TH",
                is_active=True,
            )
        )

        use_case = SeedTakeoffFromTemplate(
            project_repo=projects,
            template_repo=templates,
            template_line_repo=template_lines,
            item_repo=items,
            takeoff_repo=takeoffs,
            takeoff_line_repo=takeoff_lines,
        )

        with pytest.raises(InvalidInputError):
            use_case(project_code="PROJ-001", template_code="TH_DEFAULT")

    finally:
        conn.close()
