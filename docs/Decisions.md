# Business Rules — Take-Off App

This document defines the **business rules used to generate plumbing take-offs**.
These rules are independent from UI, database, or rendering logic.

---

# 1. Construction Stages

All take-off items belong to one of three construction stages.

Stages:

• Ground  
• TopOut  
• Final

These stages match Lennar’s construction and billing workflow.

---

# 2. Split Item Factors

Some items are distributed across stages using fixed factors.

Applicable items:

• MAT'L PER FIXTURE  
• LABOR PER FIXTURE  
• DBL-BOWL VANITY

Stage distribution:

| Stage | Factor |
|------|-------|
| Ground | 0.30 |
| TopOut | 0.30 |
| Final | 0.40 |

Example:

If MAT'L PER FIXTURE = 20

Ground  = 20 × 0.30  
TopOut  = 20 × 0.30  
Final   = 20 × 0.40

---

# 3. Stage-Specific Items

Some items belong strictly to one stage.

## Ground-only

• Sewer line material  
• Sewer line labor  
• Water supply material  
• Water supply labor  
• Plumbing permit

## TopOut-only

• Hose bibb installation  
• SUPPLY & INSTALL ICE MAKER  
• Bathtub installation

## Final-only

• Dishwasher install  
• Garbage disposal install  
• Water heater install  
• Finish plumbing fixtures

---

# 4. Water Heater Rules

A house uses **only one heater family** at a time.

Types:

• Tank water heater  
• Tankless water heater

Rules:

• A tank heater produces **Install Tank Water Heater = same quantity**  
• A tankless heater produces **Install Tankless Water Heater = same quantity**

Large single-family homes may contain **multiple tankless heaters**.

Example:

Tankless heaters:
- Rheem 18
- Rheem 13

Install Tankless Water Heater = 2

---

# 5. Double Bowl Vanity Rule

A double vanity bathroom is represented using a special item.

Example:

1 double vanity bathroom:

dbl_bowl = 1  
lav_faucets = 2  

2 double vanity bathrooms:

dbl_bowl = 2  
lav_faucets = 4  

Important:

Double bowl vanities **do not count as normal water outlet points**.
They are billed as a grouped item, but the real lavatory faucet count from the plan remains unchanged.

---

# 6. Water Point Calculation

Water points represent fixture outlets used for fixture-based pricing.

Formula:

```
water_points =
    lav_faucets
  + toilets
  + shower_trim_qty
  + tub_shower_trim_qty
  + kitchens
  + laundry_rooms
  - (double_bowl_vanities * 2)
```

Explanation:

• A double vanity contains two lav faucets but is billed as a grouped item  
• Therefore two outlets must be removed from the water-point formula

---

# 7. Hose Bibb Defaults

Default hose bib quantities:

• Townhomes (TH): 2  
• Villas: 2  
• Single Family (SF): 2  

Large SF homes may contain **3 hose bibbs** depending on plan design.

---

# 8. Sewer and Water Distance Defaults

Template defaults:

| Property Type | Default Distance |
|---------------|-----------------|
| TH | 25 ft |
| Villa | 25 ft |
| SF | 40 ft |

Actual values may change per project.

---

# 9. Fixture Counts From Plans

Typical fixture counts extracted from plans include:

• Kitchen faucets  
• Lavatory faucets  
• Toilets  
• Shower trim  
• Tub & shower trim  
• Laundry room  
• Hose bibbs  
• Ice makers  
• Bathtubs  

These counts are used to derive take-off quantities.

---

# 10. Tax Rules

Tax rate is fixed:

Tax = **7%**

Each item has a **taxable flag**.

Some items are marked:

**NO TAX by agreement**

In these cases tax must not be applied.

---

# 11. Valve Discount

Every take-off includes a fixed adjustment:

Valve Discount = **-112.99**

Rules:

• Applied **after stage totals**  
• Applied **before final grand total**

---

# 12. Versioning Rules

Take-offs support version snapshots.

Editable version:

CURRENT

Immutable versions:

V1  
V2  
V3  
...

Snapshots represent historical records and **must never be modified**.

---

# 13. Project Closure

When a project is marked **Closed**:

• No new take-offs may be created  
• Existing take-offs cannot be modified  
• Snapshots remain readable for auditing

---

# 14. Templates

Templates provide default take-off configurations.

Examples:

• TH template  
• Villa template  
• SF template

Rules:

• Templates may be edited at any time  
• Existing project take-offs remain independent once generated

---

# 15. Plan Reading Input Rules

The system distinguishes between:

• **Plan Reading Inputs**: values read directly from construction plans  
• **Derived Quantities**: values calculated from those readings using business rules  
• **Takeoff Lines**: final line items generated after fixture mapping

### 15.1 Plan Reading Inputs

Typical plan-reading inputs include:

• stories  
• kitchens  
• laundry_rooms  
• lav_faucets  
• toilets  
• showers  
• bathtubs  
• half_baths  
• double_bowl_vanities  
• hose_bibbs  
• ice_makers  
• water_heater_tank_qty  
• water_heater_tankless_qty  
• sewer_distance_lf  
• water_distance_lf

### 15.2 Derived Quantities Model

The following quantities are derived from plan readings:

• `water_points = lav_faucets + toilets + shower_trim_qty + tub_shower_trim_qty + kitchens + laundry_rooms - (double_bowl_vanities * 2)`  
• `shower_trim_qty = showers`  
• `tub_shower_trim_qty = bathtubs`  
• `pedestal_qty = half_baths`  
• `install_ice_maker_qty = ice_makers`  
• `install_garbage_disposal_qty = garbage_disposal_qty`  
• `install_tank_water_heater_qty = water_heater_tank_qty`  
• `install_tankless_water_heater_qty = water_heater_tankless_qty`

### 15.3 Separation of Concerns

The intended flow is:

`PlanReadingInput -> DerivedQuantities -> FixtureMapping -> TakeoffLines`

This separation reduces manual errors, supports automation, and preserves traceability.
# Architectural Decisions — Take-Off App

This document records **important architectural and design decisions** made during the development of the Take-Off App.

Each decision explains **what was decided, why it was decided, and the impact on the system**.

---

# 2026‑03 — Introduce Plan Reading Input Schema

## Decision
Introduce a structured **PlanReadingInput** schema to represent quantities read directly from architectural plans before any takeoff lines are generated.

## Context
Originally, takeoffs were created directly by manually entering line items. However, during system design it became clear that many takeoff quantities are derived from a small set of plan readings (fixture counts, kitchens, bathrooms, etc.).

To support future automation and reduce manual counting, the system needs a formal input layer representing plan data.

## Consequences

Benefits:

• Separates raw plan data from billing logic  
• Enables future automation of takeoff generation  
• Makes calculations traceable and auditable  
• Reduces manual errors during takeoff creation

Trade-offs:

• Introduces an additional domain model layer

---

# 2026‑03 — Introduce Derived Quantities Layer

## Decision
Introduce a **DerivedQuantities** intermediate model between `PlanReadingInput` and the final takeoff item mapping.

## Context
Many quantities used in takeoffs are **not read directly from the plan** but are calculated from plan inputs.

Examples include:

• water_points  
• shower_trim_qty  
• tub_shower_trim_qty  
• pedestal_qty  
• install_ice_maker_qty  
• install_water_heater quantities

Calculating these values directly during item mapping would mix business rules with item catalog logic.

## Consequences

Benefits:

• Keeps business-rule calculations isolated
• Improves system maintainability
• Allows easier testing of domain logic
• Simplifies future automation

Trade-offs:

• Adds an additional transformation step in the takeoff pipeline

---

# 2026‑03 — Layered Takeoff Generation Pipeline

## Decision
Adopt a layered takeoff generation pipeline:

`PlanReadingInput → DerivedQuantities → FixtureMapping → TakeoffLines`

## Context
The system needs to maintain a clear separation between:

1. Data read from plans
2. Business-rule calculations
3. Catalog item selection
4. Final invoice/takeoff lines

Without this separation, the system would become difficult to maintain and extend.

## Consequences

Benefits:

• Clear separation of concerns  
• Easier debugging and auditing  
• Future AI or automation tools can plug into the PlanReadingInput layer  
• Fixture catalogs can evolve without rewriting plan-reading logic

Trade-offs:

• Slightly more complex internal pipeline

---

# Notes

This document only records **architecture decisions**.

Operational rules and calculations are defined in:

`docs/BusinessRules.md`

System requirements are defined in:

`docs/SRS.md`

System architecture is defined in:

`docs/SystemDesign.md`

Do not include business rules or requirements in this document.