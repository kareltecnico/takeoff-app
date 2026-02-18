from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.application.generate_takeoff_report_output import GenerateTakeoffReportOutput
from app.application.input_sources import TakeoffInputSource
from app.application.resolve_takeoff import ResolveTakeoff
from app.config import AppConfig
from app.domain.output_format import OutputFormat
from app.domain.takeoff import Takeoff
from app.reporting.renderer_factory import RendererFactory


@dataclass(frozen=True)
class RenderTakeoff:
    renderer_factory: RendererFactory
    config: AppConfig

    def __call__(
        self,
        *,
        out: Path,
        fmt: OutputFormat,
        takeoff_input: TakeoffInputSource,
        tax_rate_override: Decimal | None = None,
    ) -> Path:
        takeoff = ResolveTakeoff()(takeoff_input=takeoff_input)

        if tax_rate_override is not None:
            takeoff = Takeoff(
                header=takeoff.header,
                tax_rate=tax_rate_override,
                lines=takeoff.lines,
            )

        renderer = self.renderer_factory.for_format(fmt)
        use_case = GenerateTakeoffReportOutput(renderer=renderer, config=self.config)
        return use_case(takeoff, out)