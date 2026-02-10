from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from app.reporting.models import TakeoffReport


@runtime_checkable
class TakeoffReportRenderer(Protocol):
    def render(self, report: TakeoffReport, output_path: Path) -> Path: ...