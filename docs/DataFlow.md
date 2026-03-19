# Data Flow — Take-Off App

## Input
- `Takeoff` (domain) contains:
  - header (project, contractor, model group, stories, models)
  - lines (items per stage)
  - tax_rate
  - valve_discount (domain)

## Mapping (Reporting Builder)
- `build_takeoff_report(takeoff)` produces `TakeoffReport`:
  - sections (GROUND / TOPOUT / FINAL)
  - each section contains immutable `ReportLine` values
  - grand totals are computed from domain totals
  - NOTE: Report layer clamps negative `total_after_discount` to 0 (Option A)

## Output
- Renderer converts `TakeoffReport` into a file:
  - PDF (`.pdf`)
  - JSON (`.json`)

# Data Flow — Take-Off App

## 1. Rendering Flow

### Input
- `Takeoff` (domain) contains:
  - header (project, contractor, model group, stories, models)
  - lines (items per stage)
  - tax_rate
  - valve_discount (domain)

### Mapping (Reporting Builder)
- `build_takeoff_report(takeoff)` produces `TakeoffReport`:
  - sections (GROUND / TOPOUT / FINAL)
  - each section contains immutable `ReportLine` values
  - grand totals are computed from domain totals
  - NOTE: Report layer clamps negative `total_after_discount` to 0 (Option A)

### Output
- Renderer converts `TakeoffReport` into a file:
  - PDF (`.pdf`)
  - JSON (`.json`)

---

## 2. Plan-Driven Generation Flow

The system supports end-to-end takeoff generation from plan readings.

Flow:

`PlanReadingInput -> DerivedQuantities -> FixtureMappingResolver -> TakeoffLines (CURRENT) -> Snapshot (optional)`

### Input
- `PlanReadingInput`
  - stories
  - kitchens
  - laundry_rooms
  - lav_faucets
  - toilets
  - showers
  - bathtubs
  - half_baths
  - double_bowl_vanities
  - hose_bibbs
  - ice_makers
  - garbage_disposals
  - water_heater_tank_qty
  - water_heater_tankless_qty
  - sewer_distance_lf
  - water_distance_lf

### Derived Layer
- Domain rules compute:
  - water_points
  - shower_trim_qty
  - tub_shower_trim_qty
  - pedestal_qty
  - install_ice_maker_qty
  - install_garbage_disposal_qty
  - install_tank_water_heater_qty
  - install_tankless_water_heater_qty

### Mapping Layer
- Template fixture mappings define default item selection by template category
- Project fixture overrides may substitute or disable mapped rules
- Mapping output becomes CURRENT takeoff lines with stage, factor, sort_order, and `mapping_id`

### Persistence
- CURRENT lines are stored in `takeoff_lines`
- Snapshot versions copy those rows into `takeoff_version_lines`
- `mapping_id` is preserved for cross-version traceability and diff behavior

### Guardrail
- If all resolved quantities are zero, or all effective mapping rules are disabled, generation fails.
- The system must not create an empty CURRENT takeoff.