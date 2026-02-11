from __future__ import annotations

from pathlib import Path

import pytest

from app.domain.stage import Stage
from app.infrastructure.takeoff_json_loader import (
    TakeoffJsonError,
    TakeoffJsonLoader,
)


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "takeoff.json"
    path.write_text(content, encoding="utf-8")
    return path


def test_loader_valid_file(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
{
  "header": {
    "project_name": "TEST",
    "contractor_name": "LENNAR",
    "model_group_display": "1331",
    "stories": 2,
    "models": ["1331"]
  },
  "tax_rate": "0.07",
  "lines": [
    {
      "stage": "GROUND",
      "qty": "1",
      "factor": "1",
      "sort_order": 1,
      "item": {
        "code": "A",
        "item_number": "A100",
        "description": "Desc",
        "unit_price": "100.00",
        "taxable": true
      }
    }
  ]
}
""",
    )

    takeoff = TakeoffJsonLoader().load(path)

    assert takeoff.header.project_name == "TEST"
    assert takeoff.tax_rate == takeoff.tax_rate  # Decimal check via equality
    assert len(takeoff.lines) == 1
    assert takeoff.lines[0].stage == Stage.GROUND


def test_missing_header_field(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
{
  "header": {},
  "tax_rate": "0.07",
  "lines": []
}
""",
    )

    with pytest.raises(TakeoffJsonError) as exc:
        TakeoffJsonLoader().load(path)

    assert "header.project_name" in str(exc.value)


def test_invalid_stage(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
{
  "header": {
    "project_name": "X",
    "contractor_name": "Y",
    "model_group_display": "M",
    "stories": 1,
    "models": ["M"]
  },
  "tax_rate": "0.07",
  "lines": [
    {
      "stage": "INVALID",
      "qty": "1",
      "factor": "1",
      "sort_order": 1,
      "item": {
        "code": "A",
        "item_number": "A1",
        "description": "Desc",
        "unit_price": "10",
        "taxable": true
      }
    }
  ]
}
""",
    )

    with pytest.raises(TakeoffJsonError) as exc:
        TakeoffJsonLoader().load(path)

    assert "Invalid stage" in str(exc.value)


def test_invalid_decimal(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
{
  "header": {
    "project_name": "X",
    "contractor_name": "Y",
    "model_group_display": "M",
    "stories": 1,
    "models": ["M"]
  },
  "tax_rate": "NOT_A_NUMBER",
  "lines": []
}
""",
    )

    with pytest.raises(TakeoffJsonError):
        TakeoffJsonLoader().load(path)
