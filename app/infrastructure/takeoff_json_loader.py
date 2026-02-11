from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine


class TakeoffJsonError(ValueError):
    """Raised when a Takeoff JSON file is invalid."""


def _req(obj: dict[str, Any], key: str, *, ctx: str) -> Any:
    if key not in obj:
        raise TakeoffJsonError(f"Missing field: {ctx}.{key}")
    return obj[key]


def _as_str(x: Any, *, ctx: str) -> str:
    if not isinstance(x, str):
        raise TakeoffJsonError(f"Expected string at {ctx}")
    return x


def _as_int(x: Any, *, ctx: str) -> int:
    if not isinstance(x, int):
        raise TakeoffJsonError(f"Expected int at {ctx}")
    return x


def _as_decimal(x: Any, *, ctx: str) -> Decimal:
    if isinstance(x, (int, float, str)):
        try:
            return Decimal(str(x))
        except Exception as e:  # pragma: no cover
            raise TakeoffJsonError(f"Invalid decimal at {ctx}: {x!r}") from e
    raise TakeoffJsonError(f"Expected number/string for decimal at {ctx}")


def _as_bool(x: Any, *, ctx: str) -> bool:
    if not isinstance(x, bool):
        raise TakeoffJsonError(f"Expected bool at {ctx}")
    return x


def _as_stage(x: Any, *, ctx: str) -> Stage:
    s = _as_str(x, ctx=ctx).upper()
    try:
        return Stage[s]
    except KeyError as e:
        allowed = ", ".join([m.name for m in Stage])
        raise TakeoffJsonError(
            f"Invalid stage at {ctx}: {s!r}. Allowed: {allowed}"
        ) from e


@dataclass(frozen=True)
class TakeoffJsonLoader:
    def load(self, path: Path) -> Takeoff:
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            raise TakeoffJsonError("Top-level JSON must be an object")

        header_obj = _req(data, "header", ctx="root")
        if not isinstance(header_obj, dict):
            raise TakeoffJsonError("Expected object at root.header")

        project_name = _as_str(
            _req(header_obj, "project_name", ctx="header"),
            ctx="header.project_name",
        )
        contractor_name = _as_str(
            _req(header_obj, "contractor_name", ctx="header"),
            ctx="header.contractor_name",
        )
        model_group_display = _as_str(
            _req(header_obj, "model_group_display", ctx="header"),
            ctx="header.model_group_display",
        )
        stories = _as_int(
            _req(header_obj, "stories", ctx="header"),
            ctx="header.stories",
        )

        models_raw = _req(header_obj, "models", ctx="header")
        if not isinstance(models_raw, list):
            raise TakeoffJsonError("Expected array at header.models")
        models = tuple(models_raw)

        header = TakeoffHeader(
            project_name=project_name,
            contractor_name=contractor_name,
            model_group_display=model_group_display,
            stories=stories,
            models=models,
        )

        tax_rate = _as_decimal(
            _req(data, "tax_rate", ctx="root"),
            ctx="root.tax_rate",
        )

        lines_obj = _req(data, "lines", ctx="root")
        if not isinstance(lines_obj, list):
            raise TakeoffJsonError("Expected array at root.lines")

        lines: list[TakeoffLine] = []
        for i, ln in enumerate(lines_obj):
            ctx = f"lines[{i}]"
            if not isinstance(ln, dict):
                raise TakeoffJsonError(f"Expected object at {ctx}")

            item_obj = _req(ln, "item", ctx=ctx)
            if not isinstance(item_obj, dict):
                raise TakeoffJsonError(f"Expected object at {ctx}.item")

            code = _as_str(
                _req(item_obj, "code", ctx=f"{ctx}.item"),
                ctx=f"{ctx}.item.code",
            )
            item_number = _as_str(
                _req(item_obj, "item_number", ctx=f"{ctx}.item"),
                ctx=f"{ctx}.item.item_number",
            )
            description = _as_str(
                _req(item_obj, "description", ctx=f"{ctx}.item"),
                ctx=f"{ctx}.item.description",
            )
            unit_price = _as_decimal(
                _req(item_obj, "unit_price", ctx=f"{ctx}.item"),
                ctx=f"{ctx}.item.unit_price",
            )
            taxable = _as_bool(
                _req(item_obj, "taxable", ctx=f"{ctx}.item"),
                ctx=f"{ctx}.item.taxable",
            )

            item = Item(
                code=code,
                item_number=item_number,
                description=description,
                details=item_obj.get("details"),
                unit_price=unit_price,
                taxable=taxable,
            )

            lines.append(
                TakeoffLine(
                    item=item,
                    stage=_as_stage(_req(ln, "stage", ctx=ctx), ctx=f"{ctx}.stage"),
                    qty=_as_decimal(_req(ln, "qty", ctx=ctx), ctx=f"{ctx}.qty"),
                    factor=_as_decimal(
                        _req(ln, "factor", ctx=ctx),
                        ctx=f"{ctx}.factor",
                    ),
                    sort_order=_as_int(
                        _req(ln, "sort_order", ctx=ctx),
                        ctx=f"{ctx}.sort_order",
                    ),
                )
            )

        return Takeoff(header=header, tax_rate=tax_rate, lines=tuple(lines))