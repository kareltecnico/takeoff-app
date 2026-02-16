# Architecture

This project follows a Clean Architecture / Hexagonal approach:

- **Domain** contains the business rules (pure Python, no I/O).
- **Application** orchestrates use cases (depends on Domain + Reporting).
- **Reporting** builds report DTOs and defines renderer ports (Protocol).
- **Infrastructure** implements adapters (PDF/CSV/JSON renderers, etc.).
- **Scripts** are developer utilities to run sample outputs.

The goal is: **domain never depends on application or infrastructure**, and rendering is done through a renderer interface.

---

## Layer responsibilities

### Domain (`app/domain/`)
- Entities and value objects: `Takeoff`, `TakeoffLine`, `Item`, `Stage`, totals, money helpers.
- Pure calculations and invariants.
- No imports from:
  - `app.application`
  - `app.infrastructure`
  - external I/O libs (ReportLab, csv, json, database clients, etc.)
  - reglas del negocio + cálculos (sin IO).

### Reporting (`app/reporting/`)
- DTOs for rendering: `TakeoffReport`, `ReportSection`, `ReportLine`, `ReportGrandTotals`.
- Builder/mapping from domain → DTO: `build_takeoff_report(...)`
- Renderer port/interface: `TakeoffReportRenderer` (Protocol)

Reporting is allowed to depend on Domain (types + computed results), but should remain I/O-free.

### Application (`app/application/`)
- Use cases that coordinate:
  - Domain input objects
  - Reporting builder
  - a renderer adapter via Protocol (port)
  - orquesta flujos (load/save/render), valida reglas de comando, coordina dependencias.
- Example:
  - `GenerateTakeoffPdf` builds a report DTO then calls `renderer.render(...)`

Application should not import Infrastructure implementations.

### Infrastructure (`app/infrastructure/`)
- Adapters implementing ports:
  - `ReportLabTakeoffPdfRenderer` (PDF)
  - `DebugJsonTakeoffReportRenderer` (JSON)
  - `CsvTakeoffReportRenderer` (CSV)
  - `IO` (PDF/CSV/JSON, repos, loaders/codecs).
- Infrastructure may depend on:
  - Reporting models + renderer Protocol
  - external libs like ReportLab, csv, json, etc.

### CLI (Adapters)
- parsea args y llama use cases (sin lógica de negocio).

### Scripts (`scripts/`)
- Local developer entry points:
  - `render_sample_pdf.py`
  - `render_sample_json.py`
  - `render_sample_csv.py`

Scripts are allowed to assemble real dependencies.

---

## Dependency rules

Allowed dependencies (arrows point to what you can import):

- `domain → (nothing)`
- `reporting → domain`
- `application → domain + reporting`
- `infrastructure → reporting (+ external libs)`
- `scripts → all layers`
- `Domain no import Application/Infrastructure.`

Disallowed examples:
- `domain → infrastructure`
- `domain → application`
- `application → infrastructure` (should use ports/Protocols instead)

---

## Main flow (Generate PDF / JSON / CSV)

1. A script builds a `Takeoff` (Domain).
2. `GenerateTakeoffPdf` (Application) calls `build_takeoff_report` (Reporting).
3. Use case calls `renderer.render(report, output_path)` (Reporting port).
4. A concrete renderer in Infrastructure writes output (PDF/JSON/CSV).
5. referencia a docs/DataFlow.md y a ADRs (ej. renderers).

---

## Key design decision: clamping totals in reports

Reports use Option A:
- Domain can compute negative `total_after_discount` (if discount exceeds total).
- Reporting clamps to `0.00` for presentation:
  - `total_after_discount = max(Decimal("0.00"), gt.total_after_discount)`

This ensures the final displayed report never shows negative totals.

---

## How to validate architecture

Run:
- `ruff check . --fix`
- `mypy app`
- `pytest`

Architecture tests ensure importing `app.domain` never pulls `application` or `infrastructure`.

