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
    """Loads a seeded Takeoff snapshot (SQLite: takeoffs + takeoff_lines)
    and renders it using the reporting pipeline (PDF/CSV/JSON).

    Snapshot lines persist TemplateLine v2 fields (stage/factor/sort_order).
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
            stories=2,  # Placeholder until stories/models are persisted.
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

            stage = getattr(ln, "stage", None) or Stage.FINAL
            factor = getattr(ln, "factor", None) or Decimal("1.0")
            sort_order = getattr(ln, "sort_order", None)
            if sort_order is None:
                sort_order = idx

            takeoff_lines.append(
                TakeoffLine(
                    item=item,
                    stage=stage,
                    qty=ln.qty,
                    factor=factor,
                    sort_order=int(sort_order),
                )
            )

        takeoff = Takeoff(
            header=header,
            tax_rate=t.tax_rate,
            lines=tuple(takeoff_lines),
        )

        renderer = self.renderer_factory.for_format(fmt)
        use_case = GenerateTakeoffReportOutput(renderer=renderer, config=self.config)
        return use_case(takeoff, out)


@dataclass(frozen=True)
class RenderTakeoffFromVersion:
    """Renders an immutable takeoff version (SQLite: takeoff_versions + takeoff_version_lines).

    Reproducible output: do NOT depend on current takeoff/template/project state.
    """

    project_repo: SqliteProjectRepository
    template_repo: SqliteTemplateRepository
    takeoff_repo: SqliteTakeoffRepository
    renderer_factory: RendererFactory
    config: AppConfig

    def __call__(self, *, version_id: str, out: Path, fmt: OutputFormat) -> Path:
        v = self.takeoff_repo.get_version(version_id=version_id)

        # Pinned at snapshot time
        project = self.project_repo.get(code=v.project_code_snapshot)
        template = self.template_repo.get(code=v.template_code_snapshot)

        header = TakeoffHeader(
            project_name=project.name,
            contractor_name=project.contractor or "",
            model_group_display=f"{template.code} - {template.name}",
            models=(template.code,),
            stories=2,
        )

        version_lines = self.takeoff_repo.list_version_lines(version_id=version_id)

        takeoff_lines: list[TakeoffLine] = []
        for ln in version_lines:
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
                    stage=Stage(ln.stage),
                    qty=ln.qty,
                    factor=ln.factor,
                    sort_order=int(ln.sort_order),
                )
            )

        takeoff = Takeoff(
            header=header,
            tax_rate=v.tax_rate_snapshot,
            lines=tuple(takeoff_lines),
        )

        renderer = self.renderer_factory.for_format(fmt)
        use_case = GenerateTakeoffReportOutput(renderer=renderer, config=self.config)
        return use_case(takeoff, out)