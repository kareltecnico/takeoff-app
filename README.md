# Take-Off App

Take-Off App is a command-line application designed to generate and manage plumbing take-off reports using a Clean Architecture approach.

It supports:

- PDF output (ReportLab)
- JSON debug output
- CSV export
- Local persistence of take-offs
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
- `SaveTakeoff`
- `SaveTakeoffFromInput`
- `LoadTakeoff`

**Infrastructure (`app/infrastructure/`)**
- PDF renderer (ReportLab)
- CSV renderer
- JSON renderer
- File-based repository
- RendererRegistry (maps OutputFormat → concrete renderer)

**CLI (`app/cli.py`)**
- Parses arguments
- Validates combinations
- Instantiates adapters
- Builds TakeoffInputSource
- Calls use cases

---

# Input Model (Polymorphic Design)

The system uses a polymorphic input abstraction:

`TakeoffInputSource` (Protocol)

Concrete implementations:

- `JsonTakeoffInput`
- `FactoryTakeoffInput`
- `RepoTakeoffInput`

This removes conditional logic from application use cases.

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

Saved takeoffs are stored locally in:

```
data/takeoffs/
```

Generated reports can be stored anywhere using `--out`.

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

Version: **v1.0 — Input Unified Architecture**

- Polymorphic input model implemented
- Save and Render share architecture
- Clean dependency boundaries enforced
- All tests passing
- Fully typed codebase
