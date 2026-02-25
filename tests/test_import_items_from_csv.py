from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.application.import_items_from_csv import ImportItemsFromCsv
from app.domain.item import Item


class _InMemoryItemRepo:
    def __init__(self) -> None:
        self.items: dict[str, Item] = {}

    def upsert(self, item: Item) -> None:
        self.items[item.code] = item

    def get(self, code: str) -> Item:
        return self.items[code]

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

    assert report.inserted_or_updated == 2
    assert report.skipped == 2
    assert len(report.errors) == 2

    a = repo.get("AAA-1")
    assert a.code == "AAA-1"
    assert a.item_number == "AAA-1"
    assert a.unit_price == Decimal("10.00")
    assert a.taxable is True

    c = repo.get("CCC-1")
    assert c.taxable is False
    assert c.details == "Details"
