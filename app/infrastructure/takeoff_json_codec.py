from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine


def _d(x: Decimal) -> str:
    # JSON-friendly representation
    return str(x)


@dataclass(frozen=True)
class TakeoffJsonCodec:
    def to_dict(self, takeoff: Takeoff) -> dict[str, Any]:
        return {
            "header": {
                "project_name": takeoff.header.project_name,
                "contractor_name": takeoff.header.contractor_name,
                "model_group_display": takeoff.header.model_group_display,
                "stories": takeoff.header.stories,
                "models": list(takeoff.header.models),
            },
            "tax_rate": _d(takeoff.tax_rate),
            "lines": [
                {
                    "stage": ln.stage.name,
                    "qty": _d(ln.qty),
                    "factor": _d(ln.factor),
                    "sort_order": ln.sort_order,
                    "item": {
                        "code": ln.item.code,
                        "item_number": ln.item.item_number,
                        "description": ln.item.description,
                        "details": ln.item.details,
                        "unit_price": _d(ln.item.unit_price),
                        "taxable": ln.item.taxable,
                    },
                }
                for ln in takeoff.lines
            ],
        }

    def from_dict(self, data: dict[str, Any]) -> Takeoff:
        header_obj = data["header"]
        header = TakeoffHeader(
            project_name=header_obj["project_name"],
            contractor_name=header_obj["contractor_name"],
            model_group_display=header_obj["model_group_display"],
            stories=int(header_obj["stories"]),
            models=tuple(header_obj["models"]),
        )

        lines: list[TakeoffLine] = []
        for row in data["lines"]:
            item_obj = row["item"]
            item = Item(
                code=item_obj["code"],
                item_number=item_obj["item_number"],
                description=item_obj["description"],
                details=item_obj.get("details"),
                unit_price=Decimal(str(item_obj["unit_price"])),
                taxable=bool(item_obj["taxable"]),
            )

            lines.append(
                TakeoffLine(
                    item=item,
                    stage=Stage[str(row["stage"]).upper()],
                    qty=Decimal(str(row["qty"])),
                    factor=Decimal(str(row["factor"])),
                    sort_order=int(row["sort_order"]),
                )
            )

        return Takeoff(
            header=header,
            tax_rate=Decimal(str(data["tax_rate"])),
            lines=tuple(lines),
        )
