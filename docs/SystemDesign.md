# SystemDesign.md

## 1. System Overview

The TakeOff App is a CLI-driven backend system designed to generate, manage, version, and export plumbing takeoffs per **project model**.

The system focuses on:

• Deterministic takeoff generation  
• Versioned snapshot storage  
• Reproducible exports (PDF / CSV / JSON / financial summary)  
• Clear separation between **plan reading**, **business rules**, and **rendering**

A project may contain multiple models, but **each model produces exactly one takeoff**.

Example:

Project: KEYS GATE II TH  
Models: 1333, 1455, 1585  

→ 3 takeoffs total

---

## 2. Core Architectural Layers

The application follows a simplified layered architecture.

```
CLI Layer
    ↓
Application Services
    ↓
Domain Logic
    ↓
Templates / Snapshot Storage
    ↓
Render / Export Layer
```

### CLI Layer

Responsible for user interaction.

Main entry point:

```
cli.py
```

Responsibilities:

• Create projects  
• Generate takeoffs  
• Create snapshots  
• Export bundles  
• Run summaries  

The CLI **never contains business rules**.

---

### Application Layer

Location:

```
app/application/
```

Responsibilities:

• Orchestrate workflows
• Call domain services
• Coordinate rendering and export

Examples:

```
render_takeoff.py
save_takeoff.py
summarize_project.py
```

These modules combine domain logic with output generation.

---

### Domain Layer

Location:

```
app/domain/
```

Contains the **core plumbing takeoff logic**.

Responsibilities:

• Fixture quantity calculations  
• Derived quantities  
• Template expansion  
• Snapshot preparation  

This layer enforces the plumbing takeoff business rules defined in **BusinessRules.md**.

---

### Templates

Location:

```
templates/
```

Templates represent **default takeoff configurations**.

Examples:

```
TH
Villa
SF
```

Templates contain default quantities such as:

• sewer distance  
• water distance  
• default hose bib count  
• fixture defaults

Templates can be edited at any time.

Project takeoffs inherit template defaults but remain **independent once created**.

---

### Snapshot System

Each takeoff generation produces a **versioned snapshot**.

Snapshots are immutable once created.

Purpose:

• preserve historical takeoffs  
• guarantee reproducibility  
• allow auditing  

Snapshots store:

• quantities  
• item mappings  
• financial totals  
• metadata

---

### Export Layer

Exports generate deliverables for different stakeholders.

Supported outputs:

• PDF (for management review)  
• CSV (for analysis)  
• JSON (for system integrations)  
• Financial summary  
• Snapshot bundle

Example output name:

```
KEYS GATE II TH (1333,1455,1585)
WILTON MANORS (3613)
```

---

## 3. Project Lifecycle

The system supports the following lifecycle.

1. Create Project  
2. Generate Takeoff per Model  
3. Produce Snapshot  
4. Export Deliverables  
5. Review / Adjust (new snapshot if needed)

Once a project is **closed**:

• No new takeoffs can be created  
• Existing takeoffs cannot be modified  
• Snapshots remain viewable for verification

---

## 4. Future Extensions

Planned improvements:

• Plan-reading input schema  
• Automatic takeoff generation from plan counts  
• Fixture specification mapping  
• Role-based access (admin vs read-only users)

These extensions will be implemented without altering the core snapshot architecture.

---

## 5. Future Extension — Derived Quantities Layer

After `PlanReadingInput`, the system will calculate a dedicated **DerivedQuantities** layer before mapping to final fixture items.

Target flow:

`PlanReadingInput -> DerivedQuantities -> FixtureMapping -> TakeoffLines -> ManualAdjustments -> Snapshot`

Purpose of this intermediate layer:

• centralize business-rule calculations  
• keep plan-reading logic separate from fixture selection  
• allow future automation of takeoff generation  
• reduce repetitive manual counting work

Examples of derived quantities:

• water_points  
• shower_trim_qty  
• tub_shower_trim_qty  
• pedestal_qty  
• install_ice_maker_qty  
• install_tank_water_heater_qty  
• install_tankless_water_heater_qty
# System Design — Take-Off App

## 1. System Overview

The TakeOff App is a CLI-driven backend system designed to generate, manage, version, and export plumbing takeoffs per project model.

The system focuses on:
- deterministic takeoff generation
- versioned snapshot storage
- reproducible exports (PDF / CSV / JSON / financial summary)
- clear separation between plan reading, business rules, mapping, and rendering

A project may contain multiple models, but each model produces exactly one takeoff.

Example:

Project: KEYS GATE II TH  
Models: 1333, 1455, 1585  
→ 3 takeoffs total

---

## 2. Core Architectural Layers

The application follows a simplified layered architecture.

```text
CLI Layer
    ↓
Application Services
    ↓
Domain Logic
    ↓
Mapping / Snapshot Storage
    ↓
Render / Export Layer
```

### CLI Layer
Responsible for user interaction.

Main entry point:
- `cli.py`

Responsibilities:
- create projects
- generate takeoffs
- create snapshots
- export bundles
- run summaries

The CLI never contains business logic.

### Application Layer
Location:
- `app/application/`

Responsibilities:
- orchestrate workflows
- call domain services
- coordinate persistence, rendering, and export

Examples:
- `render_takeoff.py`
- `save_takeoff.py`
- `summarize_project.py`
- `generate_takeoff_from_plan_reading.py`

### Domain Layer
Location:
- `app/domain/`

Responsibilities:
- plan-reading input model
- derived quantities
- fixture mapping resolution
- snapshot-safe takeoff line structures
- business-rule calculations

This layer enforces the plumbing takeoff rules defined in `BusinessRules.md`.

### Mapping Layer
The system supports template-driven fixture mapping with optional project override.

Flow:
- template fixture mapping supplies defaults
- project fixture override may substitute or disable rules
- resolved mapping produces takeoff lines with `mapping_id`

### Snapshot System
Each takeoff generation produces versioned snapshots.

Snapshots are immutable once created.

Purpose:
- preserve historical takeoffs
- guarantee reproducibility
- allow auditing

Snapshots store:
- quantities
- item mappings
- financial totals
- metadata
- traceability through `mapping_id` when available

### Export Layer
Exports generate deliverables for different stakeholders.

Supported outputs:
- PDF
- CSV
- JSON
- financial summary
- snapshot bundle

---

## 3. Implemented Plan-Driven Generation Flow

The backend now supports end-to-end plan-driven generation.

Flow:

`PlanReadingInput -> DerivedQuantities -> FixtureMapping -> TakeoffLines -> Snapshot`

Details:
1. CLI or application constructs `PlanReadingInput`
2. Domain computes `DerivedQuantities`
3. Fixture mapping resolves item selection using template rules and optional project override
4. Application persists CURRENT takeoff lines
5. Existing snapshot/version flow remains unchanged and preserves `mapping_id`

Guardrail:
- if all resolved quantities are zero, or all effective mapping rules are disabled, generation fails
- the system must not create an empty CURRENT takeoff

---

## 4. Project Lifecycle

The system supports the following lifecycle:
1. Create Project
2. Generate Takeoff per Model
3. Produce Snapshot
4. Export Deliverables
5. Review / Adjust (new snapshot if needed)

Once a project is closed:
- no new takeoffs can be created
- existing takeoffs cannot be modified
- snapshots remain viewable for verification

---

## 5. Known Limitation

Legacy duplicate lines without `mapping_id` are intentionally not structurally comparable in diff/report behavior.

The system:
- uses `mapping_id` as the structural comparison key when present
- falls back to legacy `item_code` matching only when uniquely identifiable
- triggers a guardrail warning when structural comparison would be unsafe

---

## 6. Future Extensions

Planned improvements:
- role-based access (admin vs read-only users)
- UI/frontend workflow over the stable backend
- pricing policy workflows
- optional AI-assisted plan extraction

These extensions should build on the current backend architecture rather than redesign it.