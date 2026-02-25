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
```

---

## Global Flags

### `--db-path`

Most commands use SQLite. You can point to any DB file:

```bash
python -m app.cli --db-path data/takeoff.db items list
```

Default:

- `data/takeoff.db`

---

## Items (Catalog)

### Add item

```bash
python -m app.cli --db-path data/takeoff.db items add \
  --code ITEM-001 \
  --description "Kitchen Faucet" \
  --unit-price 125.50 \
  --taxable false
```

### List items

```bash
python -m app.cli --db-path data/takeoff.db items list
```

Include inactive:

```bash
python -m app.cli --db-path data/takeoff.db items list --include-inactive
```

### Get item

```bash
python -m app.cli --db-path data/takeoff.db items get --code ITEM-001
```

### Update item

```bash
python -m app.cli --db-path data/takeoff.db items update \
  --code ITEM-001 \
  --unit-price 135.00 \
  --taxable true
```

### Delete item

```bash
python -m app.cli --db-path data/takeoff.db items delete --code ITEM-001
```

---

## Import Items from CSV (Normal mode)

Normal mode behavior:

- If a row is invalid, it is **skipped** and reported as an error.
- The import **continues** for the rest of the file.
- Duplicate ITEM NUMBER rows inside the CSV are skipped.

CSV required columns:

- `ITEM NUMBER`
- `PRICE$`
- `DESCRIPTION 1`
- `DESCRIPTION 2` (optional)
- `TAXABLE`

Run import:

```bash
python -m app.cli --db-path data/takeoff.db items import --csv inputs/Items.csv
```

---

## Projects

### Add project

```bash
python -m app.cli --db-path data/takeoff.db projects add \
  --code PROJ-001 \
  --name "Palm Glades" \
  --contractor "Lennar" \
  --foreman "JOE" \
  --active true
```

### List projects

```bash
python -m app.cli --db-path data/takeoff.db projects list
```

Include inactive:

```bash
python -m app.cli --db-path data/takeoff.db projects list --include-inactive
```

### Get project

```bash
python -m app.cli --db-path data/takeoff.db projects get --code PROJ-001
```

### Update project

```bash
python -m app.cli --db-path data/takeoff.db projects update \
  --code PROJ-001 \
  --foreman "ESTEBAN" \
  --active false
```

### Delete project

```bash
python -m app.cli --db-path data/takeoff.db projects delete --code PROJ-001
```

---

## Templates

Templates define default item sets (e.g. TH_DEFAULT, VILLAS_DEFAULT).
Template lines reference item codes (ITEM NUMBER) and quantities.

### Add template

```bash
python -m app.cli --db-path data/takeoff.db templates add \
  --code TH_DEFAULT \
  --name "Townhomes Default" \
  --category TH
```

### List templates

Active only:

```bash
python -m app.cli --db-path data/takeoff.db templates list
```

Include inactive:

```bash
python -m app.cli --db-path data/takeoff.db templates list --all
```

### Get template

```bash
python -m app.cli --db-path data/takeoff.db templates get --code TH_DEFAULT
```

### Update template

```bash
python -m app.cli --db-path data/takeoff.db templates update \
  --code TH_DEFAULT \
  --name "TH Default v2" \
  --active false
```

### Delete template

```bash
python -m app.cli --db-path data/takeoff.db templates delete --code TH_DEFAULT
```

### Add template line

Item must already exist in the Items catalog.

```bash
python -m app.cli --db-path data/takeoff.db templates add-line \
  --template TH_DEFAULT \
  --item ITEM-001 \
  --qty 2 \
  --notes "Default qty"
```

### List template lines

```bash
python -m app.cli --db-path data/takeoff.db templates list-lines --template TH_DEFAULT
```

### Remove template line

```bash
python -m app.cli --db-path data/takeoff.db templates remove-line \
  --template TH_DEFAULT \
  --item ITEM-001
```

---

## Takeoffs (Save / Render)

### Save sample takeoff to file repo

```bash
python -m app.cli save --input sample --repo-dir data/takeoffs
```

### Save takeoff from JSON

```bash
python -m app.cli save --input json --input-path inputs/takeoff.json --repo-dir data/takeoffs
```

### Render by ID

```bash
python -m app.cli render --id <TAKEOFF_ID> --repo-dir data/takeoffs --format pdf --out outputs/takeoff.pdf
```

### Render sample (with optional tax override)

```bash
python -m app.cli render --input sample --format pdf --out outputs/sample.pdf --tax-rate 0.07
```
