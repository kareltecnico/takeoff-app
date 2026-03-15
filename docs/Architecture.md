# Architecture

This project follows a Clean Architecture / Hexagonal approach.

Core principle:
> Domain never depends on Application or Infrastructure.

---

# Layers

## Domain (`app/domain/`)
- Pure business rules.
- Entities and value objects (`Takeoff`, `TakeoffLine`, totals, money).
- No I/O.
- No infrastructure imports.
- No application imports.

---

## Reporting (`app/reporting/`)
- Report DTOs (`TakeoffReport`, sections, lines).
- Report builder (`build_takeoff_report`).
- Renderer port (`TakeoffReportRenderer` Protocol).
- No concrete infrastructure logic.

---

## Application (`app/application/`)
- Use case orchestration.
- Coordinates:
  - Domain
  - Reporting builder
  - Renderer port
  - Repository port

Key use cases:

- `ResolveTakeoff`
- `RenderTakeoff`
- `SaveTakeoff`
- `SaveTakeoffFromInput`
- `LoadTakeoff`

### Input Abstraction (Important)

The system uses a polymorphic input model:

`TakeoffInputSource` (Protocol)

Concrete implementations:
- `JsonTakeoffInput`
- `FactoryTakeoffInput`
- `RepoTakeoffInput`

This removes conditional logic from use cases.

Application never reads CLI flags directly.

---

## Infrastructure (`app/infrastructure/`)
Implements adapters:

- PDF renderer (ReportLab)
- JSON debug renderer
- CSV renderer
- File-based repository
- RendererRegistry (maps OutputFormat → concrete renderer)

Infrastructure depends on Reporting.
Application depends only on the RendererFactory Protocol.

---

## CLI

CLI responsibilities:

- Parse args
- Validate combinations
- Instantiate infrastructure adapters
- Build `TakeoffInputSource`
- Call use cases

CLI contains zero business logic.

---

# Dependency Rules

Allowed:

- domain → nothing
- reporting → domain
- application → domain + reporting
- infrastructure → reporting
- cli → all layers

Forbidden:

- domain → infrastructure
- domain → application
- application → concrete infrastructure

---

# Main Flow (Render)

1. CLI builds `TakeoffInputSource`
2. `RenderTakeoff` calls `ResolveTakeoff`
3. Reporting builder maps domain → report DTO
4. RendererRegistry selects renderer
5. Infrastructure writes output

---

# Main Flow (Save)

1. CLI builds `TakeoffInputSource`
2. `SaveTakeoffFromInput`
3. ResolveTakeoff
4. SaveTakeoff (repository)
5. File stored locally

---

# Post‑MVP Extensions (CLI Workflows)

The system has evolved with additional CLI-driven workflows built on top of the existing architecture. These **do not change the architecture rules** defined above; they reuse the same layers.

New application use-cases include:

- `InspectTakeoff`
- `SummarizeProject`
- `GenerateProjectInvoice`
- `ExportRevisionBundle`

These follow the same pattern:

CLI → Application Use Case → Domain / Repository → Reporting → Renderer

The goal of these commands is operational tooling rather than core domain changes.

Examples of workflows:

- Project summaries (inspection and auditing)
- Snapshot bundle export
- Project invoice summary
- Operational diagnostics for takeoffs

All workflows still respect the dependency rules defined earlier in this document.
# Future Extension — Structured Input Modeling

A future extension of the system will introduce a structured input model for plan reading.

Conceptually:

- `PlanReadingInput` will capture quantities observed from plans
- derived business-rule calculations will transform those values into take-off quantities
- a fixture mapping layer will map those quantities to default catalog items

This future capability will still respect the current architecture:

CLI / UI -> Application Use Case -> Domain Rules -> Repository / Reporting / Renderer

The structured input model is intended to reduce repetitive manual work, not to replace the current take-off editing workflow.