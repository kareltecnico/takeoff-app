from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.application.errors import InvalidInputError
from app.application.import_items_from_csv import ImportItemsFromCsv
from app.domain.item import Item


class _InMemoryItemRepo:
    def __init__(self) -> None:
        self.items: dict[str, Item] = {}

    def upsert(self, item: Item) -> None:
        self.items[item.code] = item

    def get(self, code: str) -> Item:
        try:
            return self.items[code]
        except KeyError as e:
            raise InvalidInputError(f"Item not found: {code}") from e

    def list(self, *, include_inactive: bool = False) -> tuple[Item, ...]:
        return tuple(self.items.values())

    def delete(self, code: str) -> None:
        self.items.pop(code, None)


def test_import_items_from_csv_skips_bad_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "items.csv"
    csv_path.write_text(
        "ITEM NUMBER,PRICE$,DESCRIPTION 1,DESCRIPTION 2,TAXABLE\n"
        "AAA-1,$10.00,Desc A,,TRUE\n"
        "AAA-1,$11.00,Desc DUP,,TRUE\n"         # duplicate -> skipped
        "BBB-1,NOT_A_PRICE,Desc B,,FALSE\n"     # bad price -> skipped
        "CCC-1,$12.50,Desc C,Details,0\n",      # taxable false
        encoding="utf-8",
    )

    repo = _InMemoryItemRepo()
    report = ImportItemsFromCsv(repo=repo)(csv_path=csv_path)

    assert report.inserted == 2
    assert report.updated == 0
    assert report.skipped == 1
    assert report.conflicted == 1
    assert len(report.skipped_rows) == 1
    assert len(report.conflicted_rows) == 1
    assert report.conflicted_rows[0].row_number == 3
    assert "conflicting content" in report.conflicted_rows[0].reason
    assert report.skipped_rows[0].row_number == 4
    assert "Invalid PRICE$ value" in report.skipped_rows[0].reason

    a = repo.get("AAA_1")
    assert a.code == "AAA_1"
    assert a.item_number == "AAA-1"
    assert a.unit_price == Decimal("10.00")
    assert a.taxable is True

    c = repo.get("CCC_1")
    assert c.taxable is False
    assert c.details == "Details"


def test_import_items_from_csv_marks_conflicts_and_updates_price_only(tmp_path: Path) -> None:
    csv_path = tmp_path / "items.csv"
    csv_path.write_text(
        "ITEM NUMBER,PRICE$,DESCRIPTION 1,DESCRIPTION 2,TAXABLE\n"
        "AAA-1,$12.00,Desc A,,TRUE\n"
        "BBB-1,$11.00,Changed Desc,,TRUE\n"
        "CCC-1,$12.00,Desc C,New Details,FALSE\n"
        "DDD-1,$13.00,Desc D,,TRUE\n",
        encoding="utf-8",
    )

    repo = _InMemoryItemRepo()
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

    report = ImportItemsFromCsv(repo=repo)(csv_path=csv_path)

    assert report.inserted == 1
    assert report.updated == 1
    assert report.skipped == 0
    assert report.conflicted == 2
    assert len(report.conflicted_rows) == 2
    assert "Description differs" in report.conflicted_rows[0].reason
    assert "inactive existing item" in report.conflicted_rows[1].reason

    assert repo.get("AAA_1").unit_price == Decimal("12.00")
    assert repo.get("DDD_1").description == "Desc D"
