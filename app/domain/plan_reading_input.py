from dataclasses import dataclass


@dataclass
class PlanReadingInput:
    """
    Raw quantities read directly from architectural plans.

    This model represents the information extracted from the plan
    BEFORE applying any business rules or fixture mappings.
    """

    stories: int

    kitchens: int
    garbage_disposals: int
    laundry_rooms: int

    lav_faucets: int
    toilets: int

    showers: int
    bathtubs: int

    half_baths: int
    double_bowl_vanities: int

    hose_bibbs: int
    ice_makers: int

    water_heater_tank_qty: int
    water_heater_tankless_qty: int

    sewer_distance_lf: float
    water_distance_lf: float
