from __future__ import annotations

from decimal import Decimal

from app.application.diff_takeoff_versions import DiffTakeoffVersions
from app.application.generate_revision_report import GenerateRevisionReport


class _Line:
    def __init__(
        self,
        *,
        item_code: str,
        qty: str,
        stage: str,
        factor: str,
        unit_price: str,
        taxable: bool = True,
        mapping_id: str | None = None,
    ) -> None:
        self.item_code = item_code
        self.qty = Decimal(qty)
        self.stage = stage
        self.factor = Decimal(factor)
        self.unit_price_snapshot = Decimal(unit_price)
        self.taxable_snapshot = taxable
        self.mapping_id = mapping_id


class _Version:
    def __init__(self) -> None:
        self.tax_rate_snapshot = Decimal("0.07")
        self.valve_discount_snapshot = Decimal("0.00")


class _Repo:
    def __init__(self, version_lines: dict[str, tuple[_Line, ...]]) -> None:
        self._version_lines = version_lines

    def list_version_lines(self, *, version_id: str):
        return self._version_lines[version_id]

    def get_version(self, *, version_id: str):
        return _Version()


def test_mapped_lines_are_compared_by_mapping_id() -> None:
    repo = _Repo(
        {
            "v1": (
                _Line(
                    item_code="ITEM-001",
                    qty="10",
                    stage="ground",
                    factor="0.30",
                    unit_price="100.00",
                    mapping_id="map-ground",
                ),
            ),
            "v2": (
                _Line(
                    item_code="ITEM-001",
                    qty="12",
                    stage="ground",
                    factor="0.30",
                    unit_price="100.00",
                    mapping_id="map-ground",
                ),
            ),
        }
    )

    result = DiffTakeoffVersions(takeoff_repo=repo)(version_a="v1", version_b="v2")

    assert result.guardrail_triggered is False
    assert len(result.lines) == 1
    assert result.lines[0].comparison_key == "map-ground"
    assert result.lines[0].comparison_key_kind == "mapping_id"
    assert result.lines[0].change == "modified"


def test_item_substitution_on_same_mapping_id_is_modified_not_added_removed() -> None:
    repo = _Repo(
        {
            "v1": (
                _Line(
                    item_code="ITEM-STD",
                    qty="1",
                    stage="final",
                    factor="1.0",
                    unit_price="500.00",
                    mapping_id="map-heater",
                ),
            ),
            "v2": (
                _Line(
                    item_code="ITEM-RHEEM",
                    qty="1",
                    stage="final",
                    factor="1.0",
                    unit_price="525.00",
                    mapping_id="map-heater",
                ),
            ),
        }
    )

    result = DiffTakeoffVersions(takeoff_repo=repo)(version_a="v1", version_b="v2")

    assert result.summary() == {
        "added": 0,
        "removed": 0,
        "modified": 1,
        "unchanged": 0,
    }
    diff = result.lines[0]
    assert diff.change == "modified"
    assert diff.old.item_code == "ITEM-STD"
    assert diff.new.item_code == "ITEM-RHEEM"


def test_legacy_unique_item_code_fallback_works() -> None:
    repo = _Repo(
        {
            "v1": (
                _Line(
                    item_code="LEGACY-ITEM",
                    qty="1",
                    stage="final",
                    factor="1.0",
                    unit_price="10.00",
                    mapping_id=None,
                ),
            ),
            "v2": (
                _Line(
                    item_code="LEGACY-ITEM",
                    qty="2",
                    stage="final",
                    factor="1.0",
                    unit_price="10.00",
                    mapping_id=None,
                ),
            ),
        }
    )

    result = DiffTakeoffVersions(takeoff_repo=repo)(version_a="v1", version_b="v2")

    assert result.guardrail_triggered is False
    assert len(result.lines) == 1
    assert result.lines[0].comparison_key == "LEGACY-ITEM"
    assert result.lines[0].comparison_key_kind == "legacy_item_code"
    assert result.lines[0].change == "modified"


def test_duplicate_legacy_fallback_keys_trigger_guardrail() -> None:
    repo = _Repo(
        {
            "v1": (
                _Line(
                    item_code="LEGACY-DUP",
                    qty="1",
                    stage="ground",
                    factor="0.30",
                    unit_price="10.00",
                    mapping_id=None,
                ),
                _Line(
                    item_code="LEGACY-DUP",
                    qty="1",
                    stage="final",
                    factor="0.40",
                    unit_price="10.00",
                    mapping_id=None,
                ),
            ),
            "v2": (
                _Line(
                    item_code="LEGACY-DUP",
                    qty="1",
                    stage="ground",
                    factor="0.30",
                    unit_price="10.00",
                    mapping_id=None,
                ),
            ),
        }
    )

    result = DiffTakeoffVersions(takeoff_repo=repo)(version_a="v1", version_b="v2")

    assert result.guardrail_triggered is True
    assert result.warnings
    assert "duplicate legacy item_code fallback keys" in result.warnings[0]
    assert result.lines == ()


def test_revision_report_includes_guardrail_warning_text() -> None:
    repo = _Repo(
        {
            "v1": (
                _Line(
                    item_code="LEGACY-DUP",
                    qty="1",
                    stage="ground",
                    factor="0.30",
                    unit_price="10.00",
                    mapping_id=None,
                ),
                _Line(
                    item_code="LEGACY-DUP",
                    qty="1",
                    stage="final",
                    factor="0.40",
                    unit_price="10.00",
                    mapping_id=None,
                ),
            ),
            "v2": (
                _Line(
                    item_code="LEGACY-DUP",
                    qty="1",
                    stage="ground",
                    factor="0.30",
                    unit_price="10.00",
                    mapping_id=None,
                ),
            ),
        }
    )

    report = GenerateRevisionReport(takeoff_repo=repo)(version_a="v1", version_b="v2")
    text = report.to_text()

    assert report.warnings
    assert "WARNINGS" in text
    assert "duplicate legacy item_code fallback keys" in text
