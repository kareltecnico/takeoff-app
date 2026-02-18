from __future__ import annotations

from typing import Protocol

from app.domain.output_format import OutputFormat
from app.reporting.renderers import TakeoffReportRenderer


class RendererFactory(Protocol):
    def for_format(self, fmt: OutputFormat) -> TakeoffReportRenderer: ...