# Take-Off App

Generate a Take-Off report from domain data and render it to different outputs
(PDF, JSON, etc.) using a clean architecture approach.

## Project Structure

- `app/domain/` — business rules and calculations (no dependencies)
- `app/reporting/` — report DTOs + builder (domain -> report) + renderer port
- `app/application/` — use-cases (orchestration)
- `app/infrastructure/` — concrete renderers (ReportLab PDF, JSON debug)
- `scripts/` — local demo scripts
- `tests/` — unit tests + architecture guardrails

## Quickstart

Create venv, install deps, then:

```bash
ruff check . --fix
mypy app
pytest
