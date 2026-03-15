from app.domain.plan_reading_input import PlanReadingInput
from app.domain.derived_quantities import DerivedQuantities


def derive_quantities(plan: PlanReadingInput) -> DerivedQuantities:
    """
    Convert PlanReadingInput into DerivedQuantities
    using business rules from the TakeOff domain.
    """

    water_points = (
        plan.kitchens
        + plan.laundry_rooms
        + plan.lav_faucets
        + plan.toilets
        + plan.showers
        + plan.bathtubs
        - (plan.double_bowl_vanities * 2)
    )

    pedestal_qty = plan.half_baths

    shower_trim_qty = plan.showers
    tub_shower_trim_qty = plan.bathtubs

    install_ice_maker_qty = plan.ice_makers

    # Garbage disposal logic
    # Disposal qty must come explicitly from the plan/project input.
    # It should NOT be derived from kitchens because a secondary kitchen
    # may or may not include disposal depending on project approval.
    install_garbage_disposal_qty = plan.garbage_disposals

    install_tank_water_heater_qty = plan.water_heater_tank_qty
    install_tankless_water_heater_qty = plan.water_heater_tankless_qty

    return DerivedQuantities(
        water_points=water_points,
        pedestal_qty=pedestal_qty,
        shower_trim_qty=shower_trim_qty,
        tub_shower_trim_qty=tub_shower_trim_qty,
        install_ice_maker_qty=install_ice_maker_qty,
        install_garbage_disposal_qty=install_garbage_disposal_qty,
        install_tank_water_heater_qty=install_tank_water_heater_qty,
        install_tankless_water_heater_qty=install_tankless_water_heater_qty,
    )