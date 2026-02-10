from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.domain.takeoff import Takeoff
from app.reporting.builder import build_takeoff_report
from app.reporting.renderers import TakeoffReportRenderer


@dataclass(frozen=True)
class RenderTakeoffReport:
    """Application use-case: build a TakeoffReport DTO and render it via a renderer port."""
    renderer: TakeoffReportRenderer
    company_name: str = "LEZA'S PLUMBING"

    def __call__(
        self,
        takeoff: Takeoff,
        output_path: Path,
        *,
        created_at: datetime | None = None,
    ) -> Path:
        report = build_takeoff_report(
            takeoff,
            company_name=self.company_name,
            created_at=created_at,
        )
        return self.renderer.render(report, output_path)
