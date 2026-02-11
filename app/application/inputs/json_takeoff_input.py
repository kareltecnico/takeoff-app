from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from app.application.inputs.takeoff_input import TakeoffInput
from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine


class JsonTakeoffInput(TakeoffInput):
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Takeoff:
        data = json.loads(self._path.read_text())

        header = TakeoffHeader(
            project_name=data["project_name"],
            contractor_name=data["contractor_name"],
            model_group_display=data["model_group_display"],
            stories=data["stories"],
            models=tuple(data["models"]),
        )

        lines = []
        for row in data["lines"]:
            lines.append(
                TakeoffLine(
                    item=Item(
                        code=row["code"],
                        item_number=row["item_number"],
                        description=row["description"],
                        details=row.get("details"),
                        unit_price=Decimal(row["unit_price"]),
                        taxable=row["taxable"],
                    ),
                    stage=Stage[row["stage"]],
                    qty=Decimal(row["qty"]),
                    factor=Decimal(row["factor"]),
                    sort_order=row["sort_order"],
                )
            )

        return Takeoff(
            header=header,
            tax_rate=Decimal(data["tax_rate"]),
            lines=tuple(lines),
        )
