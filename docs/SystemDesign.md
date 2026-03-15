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