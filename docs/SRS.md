# Software Requirements Specification (SRS) — Take-Off App

## 1. Purpose

Take-Off App is an internal tool for **Leza’s Plumbing** used to create, manage, version, and generate plumbing take‑off documents used for:

- Preparing proposals for Lennar
- Calculating quantities by construction stage
- Supporting billing workflows
- Auditing historical take‑offs
- Reducing manual take‑off preparation time

The system converts **plan readings from architectural drawings** into structured take‑off documents through a deterministic pipeline of domain rules.

---

# 2. System Scope

## 2.1 In Scope (MVP)

The first version of the system will support:

• Project creation and management  
• Item catalog management  
• Model templates  
• Model group templates  
• Creation of editable CURRENT take‑offs  
• Automatic generation of take‑off lines based on domain rules  
• Manual adjustments to quantities and pricing  
• Immutable version snapshots (V1, V2, V3…)  
• PDF generation matching current company format  
• Tax handling (7%) with per‑item taxable flags  
• Valve Discount adjustment  

## 2.2 Out of Scope (Future Versions)

These features are intentionally deferred:

• Automated upgrade delta calculations  
• AI extraction of fixtures from architectural drawings  
• Visual comparison between take‑off versions  
• Integration with external accounting systems  

---

# 3. Definitions

**Project**  
A construction community or job managed by a contractor (typically Lennar).

**Model**  
A specific home design (e.g. 1333, 1455, etc.).

**Model Group**  
A set of models that share identical plumbing quantities and can use a single take‑off.

**Stages**

• Ground  
• TopOut  
• Final

These stages correspond to Lennar’s construction phases and billing schedule.

**CURRENT**  
Editable working version of a take‑off.

**Snapshot Version**  
Immutable historical record of a take‑off (V1, V2, V3...).

---

# 4. Stakeholders

Primary User  
Karel — creates and maintains take‑offs.

Internal Reviewer  
Eric — validates pricing before proposal submission.

External Partner  
Lennar — receives proposals and may request revisions.

---

# 5. System Architecture Overview

The system follows a **domain pipeline architecture**.

```
PlanReadingInput
        ↓
DerivedQuantities
        ↓
TemplateFixtureMapping
        ↓
ProjectFixtureOverride (optional)
        ↓
TakeoffLines
        ↓
PDF Rendering
```

Each layer has a single responsibility and isolates business logic from presentation.

---

# 6. Functional Requirements

## FR‑1 Project Management

The system shall allow users to:

• Create projects  
• Edit project details  
• Mark projects as In‑Course or Closed  
• Prevent modifications when a project is Closed

Project fields include:

• project_name  
• contractor_name (default Lennar)  
• status (in_course / closed)

---

## FR‑2 Item Catalog

The system shall maintain a catalog of plumbing items.

Each catalog item includes:

• internal_item_code (unique identifier)  
• lennar_item_number (optional)  
• description1  
• description2 (optional)  
• unit (EA, LF, etc.)  
• item_type (material or service)  
• default_taxable flag

Prices are **not stored globally** and are assigned per take‑off line.

---

## FR‑3 Templates

Templates provide reusable plumbing configurations.

Supported template types:

• TH (Townhome)  
• Villa  
• SF (Single Family)

Templates define:

• default hose bib quantities  
• default sewer / water distances  
• standard fixture assumptions

Templates accelerate take‑off generation and reduce repetitive configuration.

---

## FR‑4 Take‑Off Creation

Users can create a **CURRENT take‑off** for a project and model group.

Stored data includes:

• model_group_display  
• list of models  
• story count  
• fixture counts  
• pipe distances

The system shall automatically generate stage line items.

Users may manually:

• add custom lines  
• adjust quantities  
• adjust pricing  
• remove lines

---

## FR‑5 Versioning

Take‑offs support immutable version snapshots.

Editable working version:

CURRENT

Immutable snapshots:

• V1  
• V2  
• V3

Snapshots preserve historical pricing and quantities for auditing.

---

## FR‑6 PDF Generation

The system shall generate a PDF representation of a take‑off including:

• company title  
• creation date  
• stage tables  
• stage totals  
• tax calculations  
• Valve Discount  
• final grand total

The PDF format must match the company’s current proposal format.

---

## FR‑7 Tax Handling

Tax rules:

• Tax rate is fixed at **7%**  
• Each item has a taxable flag  
• Items marked "NO TAX by agreement" must never generate tax

---

## FR‑8 Valve Discount

Every take‑off includes a fixed adjustment:

Valve Discount = **‑112.99**

Rules:

• Applied after stage totals  
• Applied before final grand total

---

## FR‑9 Plan Reading Input Schema

The system shall support a structured model representing quantities read directly from construction plans.

Example inputs:

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
• garbage_disposals  
• water_heater_tank_qty  
• water_heater_tankless_qty  
• sewer_distance_lf  
• water_distance_lf

This layer represents **raw observations from plans**, before applying business rules.

---

## FR‑10 Derived Quantities

Derived quantities are calculated using domain rules.

Examples include:

• water_points  
• shower_trim_qty  
• tub_shower_trim_qty  
• pedestal_qty  
• install_ice_maker_qty  
• install_garbage_disposal_qty  
• install_tank_water_heater_qty  
• install_tankless_water_heater_qty

Example formula:

```
water_points =
  lav_faucets
+ toilets
+ showers
+ bathtubs
+ kitchens
+ laundry_rooms
- (double_bowl_vanities * 2)
```

---

## FR‑11 Default Fixture Mapping Schema

Derived quantities must be converted into **catalog items** using a mapping layer.

The mapping occurs in two steps.

### Template Mapping

Default fixture selections are defined by template:

• TH template  
• Villa template  
• SF template

Example mapping:

```
lav_faucets → Lav Faucet 4925
kitchen_faucet → Kitchen Faucet 7585
toilets → PF1501WH
```

### Project Override

Projects may override template mappings if Lennar changes fixtures.

Example:

```
Default: Lav Faucet 4925
Project override: Lav Faucet 5090
```

---

# 7. Non‑Functional Requirements

The system must satisfy:

Reliability  
No data loss; snapshots immutable.

Maintainability  
Clear Python modules and domain separation.

Auditability  
All versions retain creation timestamps.

Performance  
PDF generation must complete within seconds.

Offline capability  
The system must run without internet access.

---

# 8. Acceptance Criteria

The system is considered operational when:

• Users can create a project and generate a take‑off  
• The take‑off produces a correct PDF proposal  
• Snapshot versions preserve historical data  
• Tax rules and valve discount apply correctly  
• Manual adjustments are supported  
• Fixture counts from plans correctly generate take‑off quantities

---

# End of SRS