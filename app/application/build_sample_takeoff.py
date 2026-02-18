from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine


def D(x: str) -> Decimal:
    return Decimal(x)


@dataclass(frozen=True)
class BuildSampleTakeoff:
    def __call__(self, *, tax_rate: Decimal | None = None) -> Takeoff:
        header = TakeoffHeader(
            project_name="TEST PROJECT",
            contractor_name="LENNAR",
            model_group_display="1331",
            stories=2,
            models=("1331",),
        )

        lines = (
            TakeoffLine(
                item=Item(
                    code="WATER_HEATER_CONN",
                    item_number="A100",
                    description="Water heater connection",
                    details="Sample line item",
                    unit_price=D("250.00"),
                    taxable=True,
                ),
                stage=Stage.GROUND,
                qty=D("1"),
                factor=D("1"),
                sort_order=1,
            ),
        )

        return Takeoff(
            header=header,
            tax_rate=tax_rate or D("0.07"),
            lines=lines,
        )
