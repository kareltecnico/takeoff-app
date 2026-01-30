# Business Rules — Take-Off App

## 1. Stages
Stages are always:
- Ground
- TopOut
- Final

## 2. Line Calculations

### 2.1 Line Subtotal (pre-tax)
line_subtotal = price * qty * factor

### 2.2 Tax Amount
tax_amount = line_subtotal * TAX_RATE if taxable else 0

Where:
- TAX_RATE = 0.07 (fixed)

### 2.3 Line Total (with tax)
line_total = line_subtotal + tax_amount

## 3. Stage Totals
For each stage:
- stage_subtotal = sum(line_subtotal)
- stage_tax = sum(tax_amount)
- stage_total = stage_subtotal + stage_tax

## 4. Grand Totals
Across all stages:
- grand_subtotal = sum(stage_subtotal)
- grand_tax = sum(stage_tax)
- grand_total = grand_subtotal + grand_tax

## 5. Valve Discount
Valve Discount is applied before final grand total:
- valve_discount = -112.99 (setting)
- grand_total_after_discount = grand_total + valve_discount

## 6. Factors (Split Payments)
Factor meanings:
- 0.30 = 30%
- 0.40 = 40%
- 1.00 = 100%

## 7. Absolute Split Items (30/30/40)
These items are always split across stages:
- MAT’L PER FIXTURE-*
- LABOR PER FIXTURE-*
- DBL-BOWL VANITY-*

Rules:
- Ground factor = 0.30
- TopOut factor = 0.30
- Final factor = 0.40

## 8. Stage-only Items

### 8.1 Ground-only (100%)
These are charged only in Ground (factor = 1.00):
- MATERIAL FOR SEWER WASTE PIPE
- MATERIAL FOR WATER SUPPLY LINE
- LABOR FOR SEWER WASTE PIPE
- LABOR FOR WATER SUPPLY LINE
- PLUMBING PERMIT

Notes:
- Permit may start at 0 or $1 until approved, then updated.
- Taxable flags for these items are controlled per item; some are NO TAX by agreement.

### 8.2 TopOut-only (100%)
Charged only in TopOut:
- SUPPLY & INSTALL ICE MAKER
- HOSE BIBB INSTALLED
- Bathtub items (e.g., TUB, ALCOVE, VIK)
- Other special items if negotiated

### 8.3 Final-only
Final includes:
- Install services:
  - INSTALL DISHWASHER
  - INSTALL WATER HEATER (Tank)
  - INSTALL TANKLESS WATER HEATER (Tankless)
  - INSTALL GARBAGE DISPOSAL
- Finish fixtures/materials:
  - toilets, faucets, trims, water heaters, disposals, pedestals, etc.
- Special projects may add more items (negotiated)

## 9. Fixture Count Rules
- Each “water outlet point” from the plan counts 1:1 as a fixture point.
- Fixture count may be fractional (e.g., +0.5) due to negotiated special agreements.
- Fixture count drives both MAT’L PER FIXTURE and LABOR PER FIXTURE quantities.

## 10. DBL-BOWL VANITY Rules
- DBL-BOWL VANITY quantity equals the number of bathrooms with double sinks.
- Each double-vanity bathroom counts as 1 (even if it has 2 sinks).
- If present, it appears in all stages with the 30/30/40 split.

## 11. Model Grouping
Models can be grouped into a single take-off only if:
- the item list and quantities are identical (exact match).

## 12. Tax Rules
- Tax rate is fixed 7%.
- Taxability is controlled per item/line; some material-like lines are NO TAX by agreement.
- Services are generally not taxed, but the system must rely on explicit taxable flags, not assumptions.

## 13. Water Heater Install Logic
- If heater_type = tankless, use INSTALL TANKLESS WATER HEATER.
- If heater_type = tank, use INSTALL WATER HEATER.
- Installation qty must match heater qty (e.g., 2 heaters => install qty 2).

## 14. Versioning Rules
- CURRENT is editable.
- Versions (V1/V2/...) are immutable snapshots.
- Price and taxable flags are frozen in versions even if the item catalog changes later.
