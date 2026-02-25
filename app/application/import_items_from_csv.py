from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.application.errors import InvalidInputError
from app.application.repositories.item_repository import ItemRepository
from app.domain.item import Item


@dataclass(frozen=True)
class ImportItemsReport:
    inserted_or_updated: int
    skipped: int
    errors: tuple[str, ...]


def _parse_price(raw: str) -> Decimal:
    # Accept: "$1,234.56", "1234.56", "  99.00 "
    cleaned = raw.strip().replace("$", "").replace(",", "")
    if cleaned == "":
        raise InvalidInputError("PRICE$ is empty")
    try:
        return Decimal(cleaned)
    except InvalidOperation as e:
        raise InvalidInputError(f"Invalid PRICE$ value: {raw!r}") from e


def _parse_bool(raw: object) -> bool:
    # Accept: True/False, "TRUE"/"FALSE", "1"/"0", "yes"/"no"
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    s = str(raw).strip().lower()
    if s in {"true", "t", "1", "yes", "y", "on"}:
        return True
    if s in {"false", "f", "0", "no", "n", "off", ""}:
        return False
    raise InvalidInputError(f"Invalid TAXABLE value: {raw!r} (use true/false)")


def _normalize_optional_text(raw: object) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "":
        return None
    return s


class ImportItemsFromCsv:
    """
    Import items from a CSV exported from Excel.

    Normal mode behavior:
    - Any invalid row is reported as an error and skipped.
    - The import continues for the rest of the rows.
    - If a duplicate ITEM NUMBER appears in the same CSV, that row is skipped.

    KEY RULE:
    - ITEM NUMBER is the unique identifier and is used as the internal `code`.
    """

    def __init__(self, *, repo: ItemRepository) -> None:
        self._repo = repo

    def __call__(self, *, csv_path: Path) -> ImportItemsReport:
        if not csv_path.exists():
            raise InvalidInputError(f"CSV not found: {csv_path}")

        required = {"ITEM NUMBER", "PRICE$", "DESCRIPTION 1", "TAXABLE"}

        inserted_or_updated = 0
        skipped = 0
        errors: list[str] = []

        seen_item_numbers: set[str] = set()

        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                raise InvalidInputError("CSV has no header row")

            header = {h.strip() for h in reader.fieldnames if h}
            missing = sorted(required - header)
            if missing:
                raise InvalidInputError(f"CSV missing required columns: {missing}")

            for row_index, row in enumerate(reader, start=2):  # header is row 1
                try:
                    item_number = (row.get("ITEM NUMBER") or "").strip()
                    if not item_number:
                        raise InvalidInputError("ITEM NUMBER is empty")

                    if item_number in seen_item_numbers:
                        raise InvalidInputError(
                            f"Duplicate ITEM NUMBER in CSV: {item_number}"
                        )
                    seen_item_numbers.add(item_number)

                    price = _parse_price(str(row.get("PRICE$", "") or ""))
                    desc1 = (row.get("DESCRIPTION 1") or "").strip()
                    if not desc1:
                        raise InvalidInputError("DESCRIPTION 1 is empty")

                    desc2 = _normalize_optional_text(row.get("DESCRIPTION 2"))
                    taxable = _parse_bool(row.get("TAXABLE"))

                    item = Item(
                        code=item_number,          # ✅ internal code = item number
                        item_number=item_number,   # ✅ keep original field too
                        description=desc1,
                        details=desc2,
                        unit_price=price,
                        taxable=taxable,
                        is_active=True,
                    )

                    self._repo.upsert(item)
                    inserted_or_updated += 1

                except Exception as e:
                    skipped += 1
                    errors.append(f"Row {row_index}: {e}")

        return ImportItemsReport(
            inserted_or_updated=inserted_or_updated,
            skipped=skipped,
            errors=tuple(errors),
        )
