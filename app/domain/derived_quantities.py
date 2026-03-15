from dataclasses import dataclass


@dataclass
class DerivedQuantities:
    """
    Quantities derived from PlanReadingInput using domain business rules.

    This model represents calculated values that will later be mapped
    to specific fixture items in the ItemCatalog.
    """

    water_points: int

    pedestal_qty: int

    shower_trim_qty: int
    tub_shower_trim_qty: int

    install_ice_maker_qty: int

    # Garbage disposal logic
    # Disposal qty must come explicitly from the plan/project input.
    # It should NOT be derived from kitchens because a secondary kitchen
    # may or may not include disposal depending on project approval.
    install_garbage_disposal_qty: int

    install_tank_water_heater_qty: int
    install_tankless_water_heater_qty: int
