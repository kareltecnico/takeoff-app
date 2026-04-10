from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from app.application.errors import InvalidInputError
from app.application.repositories.item_repository import ItemRepository
from app.application.repositories.project_fixture_override_repository import (
    ProjectFixtureOverrideRepository,
)
from app.application.repositories.project_repository import ProjectRepository
from app.application.repositories.template_fixture_mapping_repository import (
    TemplateFixtureMappingRepository,
)
from app.application.repositories.template_repository import TemplateRepository
from app.domain.derive_takeoff_quantities import derive_quantities
from app.domain.fixture_mapping import FixtureMappingResolver
from app.domain.plan_reading_input import PlanReadingInput
from app.domain.takeoff_line_snapshot import TakeoffLineSnapshot
from app.domain.takeoff_record import TakeoffRecord


class TakeoffSnapshotRepository(Protocol):
    def create(self, takeoff: TakeoffRecord) -> None: ...


class TakeoffLineSnapshotRepository(Protocol):
    def bulk_insert(self, lines: list[TakeoffLineSnapshot]) -> None: ...


@dataclass(frozen=True)
class GenerateTakeoffFromPlanReading:
    project_repo: ProjectRepository
    template_repo: TemplateRepository
    template_fixture_mapping_repo: TemplateFixtureMappingRepository
    project_fixture_override_repo: ProjectFixtureOverrideRepository
    item_repo: ItemRepository
    takeoff_repo: TakeoffSnapshotRepository
    takeoff_line_repo: TakeoffLineSnapshotRepository
    resolver: FixtureMappingResolver = field(default_factory=FixtureMappingResolver)

    def __call__(
        self,
        *,
        project_code: str,
        template_code: str,
        model_display: str | None = None,
        plan: PlanReadingInput,
        tax_rate_override: Decimal | None = None,
    ) -> str:
        if not project_code.strip():
            raise InvalidInputError("project_code cannot be empty")
        if not template_code.strip():
            raise InvalidInputError("template_code cannot be empty")

        project = self.project_repo.get(project_code)
        _ = self.template_repo.get(template_code)

        existing = None
        try:
            existing = self.takeoff_repo.find_by_project_template(
                project_code=project_code,
                template_code=template_code,
            )
        except AttributeError:
            existing = None

        if existing is not None:
            raise InvalidInputError(
                f"Takeoff already exists for project={project_code} "
                f"template={template_code} id={existing.takeoff_id}"
            )

        rules = self.template_fixture_mapping_repo.list_for_template(template_code)
        overrides = self.project_fixture_override_repo.list_for_project(project_code)
        derived = derive_quantities(plan)

        mapped_lines = self.resolver.resolve(
            project_code=project_code,
            rules=rules,
            overrides=overrides,
            plan=plan,
            derived=derived,
        )
        if not mapped_lines:
            raise InvalidInputError(
                "Takeoff generation produced no resolved lines "
                f"for project={project_code} template={template_code}"
            )

        takeoff_id = str(uuid4())
        tax_rate = tax_rate_override if tax_rate_override is not None else Decimal("0.07")
        takeoff = TakeoffRecord(
            takeoff_id=takeoff_id,
            project_code=project_code,
            template_code=template_code,
            tax_rate=tax_rate,
            model_display=model_display.strip() if model_display is not None and model_display.strip() else None,
            valve_discount=project.valve_discount,
            created_at="",
        )

        snapshots: list[TakeoffLineSnapshot] = []
        for mapped_line in mapped_lines:
            item = self.item_repo.get(mapped_line.item_code)
            snapshots.append(
                TakeoffLineSnapshot(
                    takeoff_id=takeoff_id,
                    item_code=mapped_line.item_code,
                    mapping_id=mapped_line.mapping_id,
                    qty=mapped_line.qty,
                    notes=mapped_line.notes,
                    description_snapshot=item.description,
                    details_snapshot=item.details,
                    unit_price_snapshot=item.unit_price,
                    taxable_snapshot=item.taxable,
                    stage=mapped_line.stage,
                    factor=mapped_line.factor,
                    sort_order=mapped_line.sort_order,
                )
            )

        self.takeoff_repo.create(takeoff)
        self.takeoff_line_repo.bulk_insert(snapshots)
        return takeoff_id
