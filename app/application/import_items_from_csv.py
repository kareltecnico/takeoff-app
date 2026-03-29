from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.application.errors import InvalidInputError
from app.application.repositories.item_repository import ItemRepository
from app.domain.item import Item


_CODE_INVALID_CHARS = re.compile(r"[^A-Z0-9_]")
_CODE_SEPARATOR_RUNS = re.compile(r"[\s\-/\.]+")
_CODE_MULTI_UNDERSCORE = re.compile(r"_+")


@dataclass(frozen=True)
class ImportRowIssue:
    row_number: int
    code: str | None
    reason: str


@dataclass(frozen=True)
class ImportItemsReport:
    inserted: int
    updated: int
    skipped: int
    conflicted: int
    skipped_rows: tuple[ImportRowIssue, ...]
    conflicted_rows: tuple[ImportRowIssue, ...]


def _parse_price(raw: str) -> Decimal:
    cleaned = raw.strip().replace("$", "").replace(",", "")
    if cleaned == "":
        raise InvalidInputError("PRICE$ is empty")
    try:
        return Decimal(cleaned)
    except InvalidOperation as e:
        raise InvalidInputError(f"Invalid PRICE$ value: {raw!r}") from e


def _parse_bool(raw: object) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        raise InvalidInputError("TAXABLE is empty")
    s = str(raw).strip().lower()
    if s in {"true", "t", "1", "yes", "y", "on"}:
        return True
    if s in {"false", "f", "0", "no", "n", "off"}:
        return False
    raise InvalidInputError(f"Invalid TAXABLE value: {raw!r} (use true/false)")


def _normalize_optional_text(raw: object) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def normalize_imported_item_code(item_number: str) -> str:
    trimmed = item_number.strip()
    if trimmed == "":
        raise InvalidInputError("ITEM NUMBER is empty")

    normalized = trimmed.upper()
    normalized = _CODE_SEPARATOR_RUNS.sub("_", normalized)
    normalized = _CODE_MULTI_UNDERSCORE.sub("_", normalized).strip("_")

    if normalized == "":
        raise InvalidInputError("ITEM NUMBER normalized to an empty code")
    if _CODE_INVALID_CHARS.search(normalized):
        raise InvalidInputError(
            f"ITEM NUMBER contains unsupported characters after normalization: {item_number!r}"
        )
    return normalized


def _same_signature(
    *,
    item_number: str,
    description: str,
    details: str | None,
    taxable: bool,
    price: Decimal,
    other: tuple[str, str, str | None, bool, Decimal],
) -> bool:
    return other == (item_number, description, details, taxable, price)


def _try_get(repo: ItemRepository, code: str) -> Item | None:
    try:
        return repo.get(code)
    except InvalidInputError:
        return None


class ImportItemsFromCsv:
    """
    Controlled one-time import for trusted standard items.

    Rules:
    - Use ITEM NUMBER to derive internal code.
    - Never silently overwrite semantic conflicts.
    - Continue processing after row-level failures/conflicts.
    """

    def __init__(self, *, repo: ItemRepository) -> None:
        self._repo = repo

    def __call__(self, *, csv_path: Path) -> ImportItemsReport:
        if not csv_path.exists():
            raise InvalidInputError(f"CSV not found: {csv_path}")

        required = {"ITEM NUMBER", "PRICE$", "DESCRIPTION 1", "TAXABLE"}

        inserted = 0
        updated = 0
        skipped = 0
        conflicted = 0
        skipped_rows: list[ImportRowIssue] = []
        conflicted_rows: list[ImportRowIssue] = []

        seen_rows: dict[str, tuple[str, str, str | None, bool, Decimal]] = {}

        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                raise InvalidInputError("CSV has no header row")

            header = {h.strip() for h in reader.fieldnames if h}
            missing = sorted(required - header)
            if missing:
                raise InvalidInputError(f"CSV missing required columns: {missing}")

            for row_number, row in enumerate(reader, start=2):
                code: str | None = None
                try:
                    item_number = (row.get("ITEM NUMBER") or "").strip()
                    code = normalize_imported_item_code(item_number)

                    description = (row.get("DESCRIPTION 1") or "").strip()
                    if not description:
                        raise InvalidInputError("DESCRIPTION 1 is empty")

                    details = _normalize_optional_text(row.get("DESCRIPTION 2"))
                    taxable = _parse_bool(row.get("TAXABLE"))
                    price = _parse_price(str(row.get("PRICE$", "") or ""))

                    signature = (item_number, description, details, taxable, price)
                    previous = seen_rows.get(code)
                    if previous is not None:
                        if _same_signature(
                            item_number=item_number,
                            description=description,
                            details=details,
                            taxable=taxable,
                            price=price,
                            other=previous,
                        ):
                            skipped += 1
                            skipped_rows.append(
                                ImportRowIssue(
                                    row_number=row_number,
                                    code=code,
                                    reason="Duplicate row in CSV with identical normalized content",
                                )
                            )
                        else:
                            conflicted += 1
                            conflicted_rows.append(
                                ImportRowIssue(
                                    row_number=row_number,
                                    code=code,
                                    reason="Duplicate normalized code in CSV with conflicting content",
                                )
                            )
                        continue
                    seen_rows[code] = signature

                    current = _try_get(self._repo, code)
                    if current is None:
                        self._repo.upsert(
                            Item(
                                code=code,
                                item_number=item_number,
                                description=description,
                                details=details,
                                unit_price=price,
                                taxable=taxable,
                                is_active=True,
                                category=None,
                            )
                        )
                        inserted += 1
                        continue

                    if not current.is_active:
                        conflicted += 1
                        conflicted_rows.append(
                            ImportRowIssue(
                                row_number=row_number,
                                code=code,
                                reason="Matched an inactive existing item; manual review required",
                            )
                        )
                        continue

                    if current.description != description:
                        conflicted += 1
                        conflicted_rows.append(
                            ImportRowIssue(
                                row_number=row_number,
                                code=code,
                                reason="Description differs from active existing item",
                            )
                        )
                        continue

                    if current.taxable != taxable:
                        conflicted += 1
                        conflicted_rows.append(
                            ImportRowIssue(
                                row_number=row_number,
                                code=code,
                                reason="Taxable flag differs from active existing item",
                            )
                        )
                        continue

                    if current.item_number not in {None, item_number}:
                        conflicted += 1
                        conflicted_rows.append(
                            ImportRowIssue(
                                row_number=row_number,
                                code=code,
                                reason="External item_number differs from active existing item",
                            )
                        )
                        continue

                    if current.details is not None and details is not None and current.details != details:
                        conflicted += 1
                        conflicted_rows.append(
                            ImportRowIssue(
                                row_number=row_number,
                                code=code,
                                reason="Details differ from active existing item",
                            )
                        )
                        continue

                    changed = False
                    new_item_number = current.item_number
                    new_details = current.details
                    new_price = current.unit_price

                    if current.item_number is None and item_number:
                        new_item_number = item_number
                        changed = True

                    if current.details is None and details is not None:
                        new_details = details
                        changed = True

                    if current.unit_price != price:
                        new_price = price
                        changed = True

                    if changed:
                        self._repo.upsert(
                            Item(
                                code=current.code,
                                item_number=new_item_number,
                                description=current.description,
                                details=new_details,
                                unit_price=new_price,
                                taxable=current.taxable,
                                is_active=current.is_active,
                                category=current.category,
                            )
                        )
                        updated += 1
                    else:
                        skipped += 1
                        skipped_rows.append(
                            ImportRowIssue(
                                row_number=row_number,
                                code=code,
                                reason="No changes compared with active existing item",
                            )
                        )

                except InvalidInputError as e:
                    skipped += 1
                    skipped_rows.append(
                        ImportRowIssue(
                            row_number=row_number,
                            code=code,
                            reason=str(e),
                        )
                    )

        return ImportItemsReport(
            inserted=inserted,
            updated=updated,
            skipped=skipped,
            conflicted=conflicted,
            skipped_rows=tuple(skipped_rows),
            conflicted_rows=tuple(conflicted_rows),
        )
