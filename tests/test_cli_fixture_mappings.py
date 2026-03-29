from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from app.cli import main
from app.domain.item import Item
from app.domain.template import Template
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository


def _seed_template_and_items(db_path: Path) -> None:
    conn = SqliteDb(path=db_path).connect()
    try:
        SqliteTemplateRepository(conn=conn).upsert(
            Template(
                code="TH_DEFAULT",
                name="Townhomes Default",
                category="TH",
                is_active=True,
            )
        )
        repo = SqliteItemRepository(conn=conn)
        repo.upsert(
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
        repo.upsert(
            Item(
                code="ITEM_002",
                item_number="ITEM_002",
                description="Fixture B",
                details=None,
                unit_price=Decimal("11.00"),
                taxable=True,
                is_active=True,
            )
        )
    finally:
        conn.close()


def test_cli_fixture_mappings_full_operability(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "takeoff.db"
    _seed_template_and_items(db_path)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "add",
            "--template",
            "TH_DEFAULT",
            "--source-kind",
            "derived",
            "--source-name",
            "water_points",
            "--item",
            "ITEM_001",
            "--stage",
            "ground",
            "--factor",
            "0.30",
            "--sort-order",
            "10",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    match = re.search(r"mapping_id=([a-f0-9]+)", output)
    assert match is not None
    mapping_id = match.group(1)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "show",
            "--mapping-id",
            mapping_id,
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert "source_kind=derived" in output
    assert "ITEM_001" in output

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "update",
            "--mapping-id",
            mapping_id,
            "--source-kind",
            "constant",
            "--constant-qty",
            "2",
            "--item",
            "ITEM_002",
            "--stage",
            "final",
            "--factor",
            "1.0",
            "--sort-order",
            "20",
        ]
    )
    assert rc == 0

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "show",
            "--mapping-id",
            mapping_id,
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert mapping_id in output
    assert "source_kind=constant" in output
    assert "source_name=None" in output
    assert "constant_qty=2" in output
    assert "ITEM_002" in output

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "deactivate",
            "--mapping-id",
            mapping_id,
        ]
    )
    assert rc == 0
    _ = capsys.readouterr()

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "list",
            "--template",
            "TH_DEFAULT",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert mapping_id not in output

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "activate",
            "--mapping-id",
            mapping_id,
        ]
    )
    assert rc == 0
    _ = capsys.readouterr()

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "list",
            "--template",
            "TH_DEFAULT",
            "--include-inactive",
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert mapping_id in output


def test_cli_fixture_mappings_reject_invalid_final_state(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "takeoff.db"
    _seed_template_and_items(db_path)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "add",
            "--template",
            "TH_DEFAULT",
            "--source-kind",
            "derived",
            "--source-name",
            "water_points",
            "--item",
            "ITEM_001",
        ]
    )
    assert rc == 0

    output = capsys.readouterr().out
    mapping_id = re.search(r"mapping_id=([a-f0-9]+)", output).group(1)

    rc = main(
        [
            "--db-path",
            str(db_path),
            "fixture-mappings",
            "update",
            "--mapping-id",
            mapping_id,
            "--source-kind",
            "constant",
        ]
    )
    assert rc == 2
