from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.application.errors import InvalidInputError
from app.application.templates import Templates
from app.domain.item import Item
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_template_line_repository import SqliteTemplateLineRepository
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository


def _make_db(tmp_path: Path):
    db_path = tmp_path / "test_takeoff.db"
    conn = SqliteDb(path=db_path).connect()
    return conn


def _make_templates_service(conn):
    item_repo = SqliteItemRepository(conn=conn)
    templates_repo = SqliteTemplateRepository(conn=conn)
    lines_repo = SqliteTemplateLineRepository(conn=conn)
    return Templates(
        templates_repo=templates_repo,
        lines_repo=lines_repo,
        items_repo=item_repo,
    )


def test_templates_crud(tmp_path: Path) -> None:
    conn = _make_db(tmp_path)
    try:
        svc = _make_templates_service(conn)

        # Add
        svc.add(code="TH_DEFAULT", name="Townhomes Default", category="TH", is_active=True)

        # Get
        t = svc.get(code="TH_DEFAULT")
        assert t.code == "TH_DEFAULT"
        assert t.name == "Townhomes Default"
        assert t.category == "TH"
        assert t.is_active is True

        # List
        rows = svc.list(include_inactive=False)
        assert len(rows) == 1
        assert rows[0].code == "TH_DEFAULT"

        # Update
        svc.update(code="TH_DEFAULT", name="TH Default v2", is_active=False)
        t2 = svc.get(code="TH_DEFAULT")
        assert t2.name == "TH Default v2"
        assert t2.is_active is False

        # List inactive excluded by default
        rows2 = svc.list(include_inactive=False)
        assert len(rows2) == 0

        # List including inactive
        rows3 = svc.list(include_inactive=True)
        assert len(rows3) == 1
        assert rows3[0].is_active is False

        # Delete
        svc.delete(code="TH_DEFAULT")
        with pytest.raises(InvalidInputError):
            svc.get(code="TH_DEFAULT")

    finally:
        conn.close()


def test_template_lines_add_list_remove(tmp_path: Path) -> None:
    conn = _make_db(tmp_path)
    try:
        svc = _make_templates_service(conn)

        # Need an item to exist (service validates item exists)
        item_repo = SqliteItemRepository(conn=conn)
        item_repo.upsert(
            Item(
                code="ITEM-001",
                item_number="ITEM-001",
                description="Test Item",
                details=None,
                unit_price=Decimal("10.00"),
                taxable=False,
                is_active=True,
            )
        )

        # Add template
        svc.add(code="VILLAS_DEFAULT", name="Villas Default", category="VILLAS", is_active=True)

        # Add line
        svc.add_line(
            template_code="VILLAS_DEFAULT",
            item_code="ITEM-001",
            qty=Decimal("2"),
            notes="Default qty for villas",
        )

        lines = svc.list_lines(template_code="VILLAS_DEFAULT")
        assert len(lines) == 1
        assert lines[0].template_code == "VILLAS_DEFAULT"
        assert lines[0].item_code == "ITEM-001"
        assert lines[0].qty == Decimal("2")
        assert lines[0].notes == "Default qty for villas"

        # Remove line
        svc.remove_line(template_code="VILLAS_DEFAULT", item_code="ITEM-001")
        lines2 = svc.list_lines(template_code="VILLAS_DEFAULT")
        assert len(lines2) == 0

    finally:
        conn.close()


def test_add_line_requires_existing_item(tmp_path: Path) -> None:
    conn = _make_db(tmp_path)
    try:
        svc = _make_templates_service(conn)

        svc.add(code="TH_DEFAULT", name="Townhomes Default", category="TH", is_active=True)

        with pytest.raises(InvalidInputError):
            svc.add_line(
                template_code="TH_DEFAULT",
                item_code="ITEM-NOT-EXIST",
                qty=Decimal("1"),
                notes=None,
            )

    finally:
        conn.close()
