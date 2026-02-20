from __future__ import annotations

from dataclasses import dataclass

from app.domain.output_format import OutputFormat
from app.infrastructure.csv_takeoff_renderer import CsvTakeoffReportRenderer
from app.infrastructure.debug_takeoff_json_renderer import DebugJsonTakeoffReportRenderer
from app.infrastructure.pdf_takeoff_reportlab import ReportLabTakeoffPdfRenderer
from app.reporting.renderers import TakeoffReportRenderer


@dataclass(frozen=True)
class RendererRegistry:
    def for_format(self, fmt: OutputFormat) -> TakeoffReportRenderer:
        match fmt:
            case OutputFormat.PDF:
                return ReportLabTakeoffPdfRenderer()
            case OutputFormat.JSON:
                return DebugJsonTakeoffReportRenderer()
            case OutputFormat.CSV:
                return CsvTakeoffReportRenderer()
            case _:
                raise AssertionError(f"Unhandled format: {fmt}")