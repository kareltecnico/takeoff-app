# Take-Off App

Take-Off App is a command-line application designed to generate and manage plumbing take-off reports using a Clean Architecture approach.

It supports:

- PDF output (ReportLab)
- JSON output
- CSV export
- SQLite persistence for projects, templates, takeoffs, and snapshots
- Snapshot versioning with immutable revision history
- Integrity hash verification for versioned snapshots
- Project summary, export, package, and invoice workflows
- Strong typing with mypy
- Static analysis with ruff
- Automated testing with pytest

---

# Project Goals

This project was built following strict software engineering principles:

- Clear separation of layers
- Domain-driven structure
- No business logic in CLI
- No infrastructure dependencies inside domain
- Fully typed Python codebase
- Test-first mindset

---

# Architecture Overview

The system follows a Clean Architecture / Hexagonal Architecture design.

### Layers

**Domain (`app/domain/`)**
- Core business rules
- Entities and value objects
- No I/O
- No infrastructure dependencies

**Reporting (`app/reporting/`)**
- Report DTOs
- Report builder
- Renderer port (Protocol)

**Application (`app/application/`)**
- Use case orchestration
- Coordinates domain, reporting, repository, and renderer

Key use cases:
- `ResolveTakeoff`
- `RenderTakeoff`
- `RenderTakeoffFromVersion`
- `SaveTakeoff`
- `SaveTakeoffFromInput`
- `LoadTakeoff`
- `InspectTakeoff`
- `SummarizeProject`
- `GenerateProjectInvoice`
- `ExportRevisionBundle`

**Infrastructure (`app/infrastructure/`)**
- PDF renderer (ReportLab)
- CSV renderer
- JSON renderer
- SQLite repositories
- SQLite schema migrations
- RendererRegistry (maps OutputFormat → concrete renderer)

**CLI (`app/cli.py`)**
- Parses arguments
- Validates combinations
- Instantiates adapters
- Builds TakeoffInputSource
- Calls use cases

---

# Business Model

The system is designed around **project + model** takeoffs.

Key assumptions:

- Takeoffs are created **per project and per model**, not per lot.
- If a project uses 3 models, it normally has 3 takeoffs.
- Project-specific changes affect only that project’s takeoff.
- Permanent future changes should later be applied to the default / standard model library.
- Snapshots represent immutable historical revisions of a takeoff.

This keeps estimating logic separated from billing or lot-level execution.

---

# Quick Start

Create and activate a virtual environment, then run:

```bash
ruff check . --fix
mypy app
pytest
```

All checks should pass.

---

# CLI Usage

You can use the application from the terminal using:

```bash
python -m app.cli <command> [options]
```

## Main SQLite Workflows

### Project Summary

```bash
python -m app.cli projects summary --code PROJ-001
```

### Project Export

```bash
python -m app.cli projects export --code PROJ-001
```

### Project Package

```bash
python -m app.cli projects package --code PROJ-001
```

### Project Invoice

```bash
python -m app.cli projects invoice --code PROJ-001
```

### Verify Snapshot Integrity

```bash
python -m app.cli takeoffs verify-version --version-id <VERSION_ID>
```

---

## Takeoff Revision Management

The system supports full revision lifecycle management for takeoffs.

Features include:

- Snapshot creation
- Revision history timeline
- Version comparison (diff)
- Financial impact diff
- Revision reports
- Revision locking and revision workflow
 - Snapshot bundle export
 - Integrity schema versioning

### View Takeoff History

Displays the full revision timeline of a takeoff.

```bash
python -m app.cli --db-path data/takeoff.db takeoffs history \
  --id <TAKEOFF_ID>
```

---

## Export Revision Bundle

A full revision deliverable can be exported as a **bundle** containing:

- Rendered Takeoff PDF
- Revision Report
- Metadata describing the revision
- Phase summary
- Integrity hash and schema version in metadata

### Command

```bash
python -m app.cli --db-path data/takeoff.db takeoffs export-revision \
  --version-id <VERSION_ID>
```

### Output Structure

The system generates a deterministic folder structure:

```
outputs/
  <project_code>/
    <template_code>/
      v<version_number>/
        takeoff_v<version>.pdf
        revision_report_v<prev>_to_v<version>.txt
        metadata.json
        phase_summary.txt
```

Example:

```
outputs/PROJ-001/TH_DEFAULT/v6/
```

This bundle represents a **complete revision deliverable** that can be:

- archived
- reviewed by supervisors
- shared with field teams

The bundle generation is deterministic and tied to the immutable snapshot version.

---

## Project Export

The system can export a full project workspace using the latest snapshot of each takeoff.

### Command

```bash
python -m app.cli projects export --code PROJ-001
```

### Export Contents

The project export currently generates:

- project summary (`json` and `txt`)
- financial summary (`txt`)
- deliverable files per model (`pdf`, `csv`, `json`)
- latest snapshot bundle per takeoff

Typical structure:

```
outputs/
  PROJ-001/
    <project_name>_(<models>)_project_summary.json
    <project_name>_(<models>)_project_summary.txt
    <project_name>_(<models>)_financial_summary.txt
    deliverable/
      <project_name>_(<model>).pdf
      <project_name>_(<model>).csv
      <project_name>_(<model>).json
    takeoffs/
      <template_code>/
        latest/
          ...snapshot bundle...
```

---

## Project Package

The system can assemble a structured project package for delivery and review.

### Command

```bash
python -m app.cli projects package --code PROJ-001
```

### Package Structure

```
outputs/
  PROJ-001_PACKAGE/
    01_SUMMARY/
    02_MODELS/
    03_SNAPSHOTS/
```

This package is intended for:

- management review
- purchasing / materials review
- project archiving
- snapshot audit trail reference

---

## Project Invoice

The system can generate a project invoice summary by construction phase.

### Command

```bash
python -m app.cli projects invoice --code PROJ-001
```

### Current Output

The invoice summary currently reports:

- stage totals for `GROUND`, `TOPOUT`, and `FINAL`
- grand totals
- model-level breakdown

This is currently a reporting / analysis workflow and not a final QuickBooks export pipeline.

---

## Render

Render generates a report (PDF, JSON, or CSV).

### Render sample to PDF

```bash
python -m app.cli render \
  --format pdf \
  --out outputs/sample.pdf
```

### Render from JSON file

```bash
python -m app.cli render \
  --input json \
  --input-path example.json \
  --format pdf \
  --out outputs/from_json.pdf
```

### Render by saved ID

```bash
python -m app.cli render \
  --id 83d55796c451 \
  --format pdf \
  --out outputs/from_repo.pdf
```

---

## Save

Save stores a takeoff into the repository.

### Save sample

```bash
python -m app.cli save
```

### Save from JSON

```bash
python -m app.cli save \
  --input json \
  --input-path example.json
```

---

# Where Data Is Stored

SQLite data is stored locally in the configured database file, typically:

```
data/takeoff.db
```

Generated reports, revision bundles, project exports, and project packages are stored under the configured output folder (for example `outputs/`).

---

# Testing & Code Quality

```bash
ruff check .
mypy app
pytest
```

---

# Documentation

See:

- docs/Architecture.md
- docs/DataFlow.md
- docs/BusinessRules.md
- docs/Roadmap.md

---

# Current Status

Version: **v2.0 — SQLite Versioned Takeoff Platform**

Implemented capabilities include:

- SQLite-backed projects, templates, template lines, takeoffs, and takeoff lines
- Takeoff revision lifecycle with snapshots, history, diff, and revision reports
- Immutable snapshot bundles with metadata, phase summaries, and integrity verification
- Project summary, export, package, and invoice summary workflows
- Render workflows for both live takeoffs and frozen versions
- Clean dependency boundaries enforced
- All tests passing
- Fully typed codebase
