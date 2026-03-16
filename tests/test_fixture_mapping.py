from decimal import Decimal

from app.domain.derive_takeoff_quantities import derive_quantities
from app.domain.fixture_mapping import (
    FixtureMappingResolver,
    FixtureQuantityRef,
    FixtureQuantitySourceKind,
    ProjectFixtureOverride,
    TemplateFixtureMappingRule,
)
from app.domain.plan_reading_input import PlanReadingInput
from app.domain.stage import Stage


def _plan() -> PlanReadingInput:
    return PlanReadingInput(
        stories=2,
        kitchens=1,
        garbage_disposals=1,
        laundry_rooms=1,
        lav_faucets=4,
        toilets=3,
        showers=2,
        bathtubs=1,
        half_baths=1,
        double_bowl_vanities=1,
        hose_bibbs=2,
        ice_makers=1,
        water_heater_tank_qty=0,
        water_heater_tankless_qty=2,
        sewer_distance_lf=40.0,
        water_distance_lf=25.0,
    )


def test_fixture_quantity_ref_resolves_from_derived() -> None:
    plan = _plan()
    derived = derive_quantities(plan)

    ref = FixtureQuantityRef(
        source_kind=FixtureQuantitySourceKind.DERIVED,
        source_name="water_points",
    )

    assert ref.resolve(plan=plan, derived=derived) == Decimal("10")


def test_fixture_quantity_ref_resolves_from_plan() -> None:
    plan = _plan()
    derived = derive_quantities(plan)

    ref = FixtureQuantityRef(
        source_kind=FixtureQuantitySourceKind.PLAN,
        source_name="sewer_distance_lf",
    )

    assert ref.resolve(plan=plan, derived=derived) == Decimal("40.0")


def test_fixture_quantity_ref_resolves_from_constant() -> None:
    plan = _plan()
    derived = derive_quantities(plan)

    ref = FixtureQuantityRef(
        source_kind=FixtureQuantitySourceKind.CONSTANT,
        constant_qty=Decimal("1"),
    )

    assert ref.resolve(plan=plan, derived=derived) == Decimal("1")


def test_fixture_mapping_resolver_applies_rules_without_overrides() -> None:
    plan = _plan()
    derived = derive_quantities(plan)
    resolver = FixtureMappingResolver()

    rules = (
        TemplateFixtureMappingRule(
            mapping_id="map-water-points-ground",
            template_code="TH_DEFAULT",
            quantity_ref=FixtureQuantityRef(
                source_kind=FixtureQuantitySourceKind.DERIVED,
                source_name="water_points",
            ),
            item_code="MAT_PER_FIXTURE",
            qty_multiplier=Decimal("1"),
            stage=Stage.GROUND,
            factor=Decimal("0.30"),
            sort_order=10,
            notes="Ground split",
        ),
        TemplateFixtureMappingRule(
            mapping_id="map-sewer-line",
            template_code="TH_DEFAULT",
            quantity_ref=FixtureQuantityRef(
                source_kind=FixtureQuantitySourceKind.PLAN,
                source_name="sewer_distance_lf",
            ),
            item_code="SEWER_LINE_MATERIAL",
            qty_multiplier=Decimal("1"),
            stage=Stage.GROUND,
            factor=Decimal("1"),
            sort_order=20,
        ),
        TemplateFixtureMappingRule(
            mapping_id="map-permit",
            template_code="TH_DEFAULT",
            quantity_ref=FixtureQuantityRef(
                source_kind=FixtureQuantitySourceKind.CONSTANT,
                constant_qty=Decimal("1"),
            ),
            item_code="PLUMBING_PERMIT",
            qty_multiplier=Decimal("1"),
            stage=Stage.GROUND,
            factor=Decimal("1"),
            sort_order=30,
        ),
    )

    lines = resolver.resolve(
        project_code="PROJ-001",
        rules=rules,
        overrides=(),
        plan=plan,
        derived=derived,
    )

    assert len(lines) == 3
    assert lines[0].mapping_id == "map-water-points-ground"
    assert lines[0].item_code == "MAT_PER_FIXTURE"
    assert lines[0].qty == Decimal("10")
    assert lines[0].stage == Stage.GROUND
    assert lines[0].factor == Decimal("0.30")
    assert lines[0].notes == "Ground split"

    assert lines[1].item_code == "SEWER_LINE_MATERIAL"
    assert lines[1].qty == Decimal("40.0")

    assert lines[2].item_code == "PLUMBING_PERMIT"
    assert lines[2].qty == Decimal("1")


def test_fixture_mapping_resolver_skips_disabled_project_override() -> None:
    plan = _plan()
    derived = derive_quantities(plan)
    resolver = FixtureMappingResolver()

    rules = (
        TemplateFixtureMappingRule(
            mapping_id="map-ice-maker",
            template_code="TH_DEFAULT",
            quantity_ref=FixtureQuantityRef(
                source_kind=FixtureQuantitySourceKind.DERIVED,
                source_name="install_ice_maker_qty",
            ),
            item_code="ICE_MAKER_STD",
            stage=Stage.TOPOUT,
        ),
    )
    overrides = (
        ProjectFixtureOverride(
            project_code="PROJ-001",
            mapping_id="map-ice-maker",
            is_disabled=True,
        ),
    )

    lines = resolver.resolve(
        project_code="PROJ-001",
        rules=rules,
        overrides=overrides,
        plan=plan,
        derived=derived,
    )

    assert lines == ()


def test_fixture_mapping_resolver_applies_item_substitution_override() -> None:
    plan = _plan()
    derived = derive_quantities(plan)
    resolver = FixtureMappingResolver()

    rules = (
        TemplateFixtureMappingRule(
            mapping_id="map-tankless-heater",
            template_code="SF_DEFAULT",
            quantity_ref=FixtureQuantityRef(
                source_kind=FixtureQuantitySourceKind.DERIVED,
                source_name="install_tankless_water_heater_qty",
            ),
            item_code="TANKLESS_STD",
            stage=Stage.FINAL,
        ),
    )
    overrides = (
        ProjectFixtureOverride(
            project_code="PROJ-001",
            mapping_id="map-tankless-heater",
            item_code_override="TANKLESS_RHEEM",
        ),
    )

    lines = resolver.resolve(
        project_code="PROJ-001",
        rules=rules,
        overrides=overrides,
        plan=plan,
        derived=derived,
    )

    assert len(lines) == 1
    assert lines[0].mapping_id == "map-tankless-heater"
    assert lines[0].item_code == "TANKLESS_RHEEM"
    assert lines[0].qty == Decimal("2")


def test_fixture_mapping_resolver_applies_notes_override() -> None:
    plan = _plan()
    derived = derive_quantities(plan)
    resolver = FixtureMappingResolver()

    rules = (
        TemplateFixtureMappingRule(
            mapping_id="map-hose-bibb",
            template_code="TH_DEFAULT",
            quantity_ref=FixtureQuantityRef(
                source_kind=FixtureQuantitySourceKind.PLAN,
                source_name="hose_bibbs",
            ),
            item_code="HOSE_BIBB_STD",
            stage=Stage.TOPOUT,
            notes="Template note",
        ),
    )
    overrides = (
        ProjectFixtureOverride(
            project_code="PROJ-001",
            mapping_id="map-hose-bibb",
            notes_override="Use upgraded hose bibb finish",
        ),
    )

    lines = resolver.resolve(
        project_code="PROJ-001",
        rules=rules,
        overrides=overrides,
        plan=plan,
        derived=derived,
    )

    assert len(lines) == 1
    assert lines[0].item_code == "HOSE_BIBB_STD"
    assert lines[0].qty == Decimal("2")
    assert lines[0].notes == "Use upgraded hose bibb finish"
