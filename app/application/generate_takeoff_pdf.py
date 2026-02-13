from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.application.generate_takeoff_report_output import GenerateTakeoffReportOutput
from app.config import AppConfig
from app.domain.takeoff import Takeoff
from app.reporting.renderers import TakeoffReportRenderer


@dataclass(frozen=True)
class GenerateTakeoffPdf:
    """
    Backward-compatible wrapper.

    NOTE: This use case name is legacy. Prefer GenerateTakeoffReportOutput.
    """

    renderer: TakeoffReportRenderer
    company_name: str = "LEZA'S PLUMBING"

    def __call__(
        self,
        takeoff: Takeoff,
        output_path: Path,
        *,
        created_at: datetime | None = None,
    ) -> Path:
        use_case = GenerateTakeoffReportOutput(
            renderer=self.renderer,
            config=AppConfig(),
        )
        return use_case(takeoff, output_path, created_at=created_at)