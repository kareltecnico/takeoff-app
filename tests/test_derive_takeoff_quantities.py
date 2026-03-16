from app.domain.derive_takeoff_quantities import derive_quantities
from app.domain.plan_reading_input import PlanReadingInput


def test_derive_quantities_applies_business_rules() -> None:
    plan = PlanReadingInput(
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
        water_distance_lf=40.0,
    )

    derived = derive_quantities(plan)

    assert derived.water_points == 10
    assert derived.pedestal_qty == 1
    assert derived.shower_trim_qty == 2
    assert derived.tub_shower_trim_qty == 1
    assert derived.install_ice_maker_qty == 1
    assert derived.install_garbage_disposal_qty == 1
    assert derived.install_tank_water_heater_qty == 0
    assert derived.install_tankless_water_heater_qty == 2
