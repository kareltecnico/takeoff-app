from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from app.application.errors import InvalidInputError
from app.application.repositories.item_repository import ItemRepository
from app.application.repositories.project_repository import ProjectRepository
from app.application.repositories.template_line_repository import TemplateLineRepository
from app.application.repositories.template_repository import TemplateRepository
from app.domain.takeoff_line_snapshot import TakeoffLineSnapshot
from app.domain.takeoff_record import TakeoffRecord


class TakeoffSnapshotRepository(Protocol):
    def create(self, takeoff: TakeoffRecord) -> None: ...


class TakeoffLineSnapshotRepository(Protocol):
    def bulk_insert(self, lines: list[TakeoffLineSnapshot]) -> None: ...

@dataclass(frozen=True)
class SeedTakeoffFromTemplate:
    project_repo: ProjectRepository
    template_repo: TemplateRepository
    template_line_repo: TemplateLineRepository
    item_repo: ItemRepository
    takeoff_repo: TakeoffSnapshotRepository
    takeoff_line_repo: TakeoffLineSnapshotRepository

    def __call__(
        self,
        *,
        project_code: str,
        template_code: str,
        tax_rate_override: Decimal | None = None,
    ) -> str:
        if not project_code.strip():
            raise InvalidInputError("project_code cannot be empty")
        if not template_code.strip():
            raise InvalidInputError("template_code cannot be empty")

        # Validate existence (raises InvalidInputError if missing)
        _ = self.project_repo.get(project_code)
        _ = self.template_repo.get(template_code)

        template_lines = self.template_line_repo.list_for_template(template_code)
        if not template_lines:
            raise InvalidInputError(f"Template has no lines: {template_code}")

        takeoff_id = str(uuid4())
        tax_rate = tax_rate_override if tax_rate_override is not None else Decimal("0.07")

        takeoff = TakeoffRecord(
            takeoff_id=takeoff_id,
            project_code=project_code,
            template_code=template_code,
            tax_rate=tax_rate,
            created_at="",
        )

        snapshots: list[TakeoffLineSnapshot] = []
        for tl in template_lines:
            item = self.item_repo.get(tl.item_code)  # validates existence

            snapshots.append(
                TakeoffLineSnapshot(
                    takeoff_id=takeoff_id,
                    item_code=tl.item_code,
                    qty=tl.qty,
                    notes=tl.notes,
                    description_snapshot=item.description,
                    details_snapshot=item.details,
                    unit_price_snapshot=item.unit_price,
                    taxable_snapshot=item.taxable,
                )
            )

        # Persist atomically
        self.takeoff_repo.create(takeoff)
        self.takeoff_line_repo.bulk_insert(snapshots)
        return takeoff_id
