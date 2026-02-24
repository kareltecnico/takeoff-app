# CLI

This project ships with a CLI to manage data and generate reports.

All examples assume you are in the repository root and your virtual environment is active.

---

## Quick Start

Run the quality gate:

```bash
ruff check . --fix
rm -rf .mypy_cache
mypy app
pytest -q
