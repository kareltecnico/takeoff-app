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