from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.cli import main
from app.domain.item import Item
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository


def test_cli_items_add_get_list_activate_deactivate(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "takeoff.db"

    rc = main(
        [
            "--db-path",
            str(db_path),
            "items",
            "add",
            "--code",
            "ITEM_001",
            "--description",
            "Kitchen Faucet",
            "--unit-price",
            "100.00",
            "--taxable",
            "true",
            "--item-number",
            "A-100",
            "--details",
            "Chrome",
        ]
    )
    assert rc == 0

    rc = main(["--db-path", str(db_path), "items", "get", "--code", "ITEM_001"])
    output = capsys.readouterr().out
    assert rc == 0
    assert "Kitchen Faucet" in output
    assert "item_number=A-100" in output

    rc = main(["--db-path", str(db_path), "items", "deactivate", "--code", "ITEM_001"])
    assert rc == 0
    _ = capsys.readouterr()

    rc = main(["--db-path", str(db_path), "items", "list"])
    output = capsys.readouterr().out
    assert rc == 0
    assert "ITEM_001" not in output

    rc = main(
        ["--db-path", str(db_path), "items", "list", "--include-inactive"]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert "ITEM_001" in output
    assert "inactive" in output

    rc = main(["--db-path", str(db_path), "items", "activate", "--code", "ITEM_001"])
    assert rc == 0
    _ = capsys.readouterr()

    rc = main(["--db-path", str(db_path), "items", "list"])
    output = capsys.readouterr().out
    assert rc == 0
    assert "ITEM_001" in output


def test_cli_items_update_can_clear_optional_fields(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "takeoff.db"
    conn = SqliteDb(path=db_path).connect()
    try:
        SqliteItemRepository(conn=conn).upsert(
            Item(
                code="ITEM_001",
                item_number="A-100",
                description="Kitchen Faucet",
                details="Chrome",
                unit_price=Decimal("100.00"),
                taxable=True,
                is_active=True,
            )
        )
    finally:
        conn.close()

    rc = main(
        [
            "--db-path",
            str(db_path),
            "items",
            "update",
            "--code",
            "ITEM_001",
            "--clear-item-number",
            "--clear-details",
        ]
    )
    assert rc == 0

    rc = main(["--db-path", str(db_path), "items", "get", "--code", "ITEM_001"])
    output = capsys.readouterr().out
    assert rc == 0
    assert "item_number=None" in output
    assert "details=None" in output


def test_cli_items_import_reports_updates_skips_and_conflicts(
    tmp_path: Path, capsys
) -> None:
    db_path = tmp_path / "takeoff.db"
    csv_path = tmp_path / "items.csv"
    csv_path.write_text(
        "ITEM NUMBER,PRICE$,DESCRIPTION 1,DESCRIPTION 2,TAXABLE\n"
        "AAA-1,$12.00,Desc A,,TRUE\n"
        "BBB-1,$11.00,Changed Desc,,TRUE\n"
        "CCC-1,$12.00,Desc C,New Details,FALSE\n"
        "DDD-1,$13.00,Desc D,,TRUE\n",
        encoding="utf-8",
    )

    conn = SqliteDb(path=db_path).connect()
    try:
        repo = SqliteItemRepository(conn=conn)
        repo.upsert(
            Item(
                code="AAA_1",
                item_number="AAA-1",
                description="Desc A",
                details=None,
                unit_price=Decimal("10.00"),
                taxable=True,
                is_active=True,
            )
        )
        repo.upsert(
            Item(
                code="BBB_1",
                item_number="BBB-1",
                description="Desc B",
                details=None,
                unit_price=Decimal("11.00"),
                taxable=True,
                is_active=True,
            )
        )
        repo.upsert(
            Item(
                code="CCC_1",
                item_number="CCC-1",
                description="Desc C",
                details=None,
                unit_price=Decimal("12.00"),
                taxable=False,
                is_active=False,
            )
        )
    finally:
        conn.close()

    rc = main(["--db-path", str(db_path), "items", "import", "--csv", str(csv_path)])
    output = capsys.readouterr().out
    assert rc == 0
    assert "inserted=1" in output
    assert "updated=1" in output
    assert "conflicted=2" in output
    assert "row=3" in output
    assert "row=4" in output
