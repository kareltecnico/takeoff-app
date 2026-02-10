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
