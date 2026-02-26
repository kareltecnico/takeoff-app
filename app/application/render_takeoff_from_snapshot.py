from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.application.generate_takeoff_report_output import GenerateTakeoffReportOutput
from app.config import AppConfig
from app.domain.item import Item
from app.domain.output_format import OutputFormat
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_takeoff_line_repository import SqliteTakeoffLineRepository
from app.infrastructure.sqlite_takeoff_repository import SqliteTakeoffRepository
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository
from app.reporting.renderer_factory import RendererFactory


@dataclass(frozen=True)
class RenderTakeoffFromSnapshot:
    """
    Application adapter: loads a seeded Takeoff snapshot (SQLite) and renders it using
    the existing reporting pipeline (PDF/CSV/JSON).

    Current limitation (intentional for this phase):
      - Snapshot lines do not include Stage/Factor/SortOrder yet.
      - We render all lines under FINAL stage with factor=1.0 and stable ordering.

    Next iteration:
      - Extend the snapshot schema to persist stage/factor/sort_order so report layout
        and stage totals match the original Takeoff model.
    """

    project_repo: SqliteProjectRepository
    template_repo: SqliteTemplateRepository
    takeoff_repo: SqliteTakeoffRepository
    takeoff_line_repo: SqliteTakeoffLineRepository
    renderer_factory: RendererFactory
    config: AppConfig

    def __call__(self, *, takeoff_id: str, out: Path, fmt: OutputFormat) -> Path:
        t = self.takeoff_repo.get(takeoff_id=takeoff_id)
        lines = self.takeoff_line_repo.list_for_takeoff(takeoff_id=takeoff_id)

        project = self.project_repo.get(code=t.project_code)
        template = self.template_repo.get(code=t.template_code)

        header = TakeoffHeader(
            project_name=project.name,
            contractor_name=project.contractor or "",
            model_group_display=f"{template.code} - {template.name}",
            models=(template.code,),
            stories=2,  # Placeholder until stories/models are persisted in templates/snapshots.
        )

        takeoff_lines: list[TakeoffLine] = []
        for idx, ln in enumerate(lines):
            item = Item(
                code=ln.item_code,
                item_number=None,
                description=ln.description_snapshot,
                details=ln.details_snapshot,
                unit_price=ln.unit_price_snapshot,
                taxable=ln.taxable_snapshot,
                is_active=True,
            )

            takeoff_lines.append(
                TakeoffLine(
                    item=item,
                    stage=Stage.FINAL,           # Placeholder (see docstring).
                    qty=ln.qty,
                    factor=Decimal("1.0"),       # Placeholder (see docstring).
                    sort_order=idx,              # Stable ordering.
                )
            )

        takeoff = Takeoff(
            header=header,
            tax_rate=t.tax_rate,  # Tax rate is fixed in snapshot (auditability).
            lines=tuple(takeoff_lines),
        )

        renderer = self.renderer_factory.for_format(fmt)
        use_case = GenerateTakeoffReportOutput(renderer=renderer, config=self.config)
        return use_case(takeoff, out)
