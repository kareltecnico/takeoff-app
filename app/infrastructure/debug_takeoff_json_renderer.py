from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.reporting.models import TakeoffReport
from app.reporting.renderers import TakeoffReportRenderer


class DebugJsonTakeoffReportRenderer(TakeoffReportRenderer):
    """
    Writes the prepared TakeoffReport DTO to disk as JSON.
    Useful for debugging and for future integrations (APIs, UI, Excel, etc.).
    """

    def render(self, report: TakeoffReport, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        payload = asdict(report)

        # Make JSON stable/readable for diffs and debugging.
        # datetime becomes string via default=str.
        text = json.dumps(payload, indent=2, sort_keys=True, default=str)

        output_path.write_text(text, encoding="utf-8")
        return output_path
