# Software Requirements Specification (SRS) — Take-Off App

## 1. Purpose
Take-Off App is an internal tool for Leza’s Plumbing to build, maintain, version, and generate Take-Off PDFs used to:
- submit proposals to Lennar,
- invoice by construction stage (Ground / TopOut / Final),
- audit payments and resolve discrepancies,
- quickly identify which fixtures/materials a given Project + Model uses.

## 2. Scope

### In Scope (MVP v1)
- Project management (create/edit, status in-course/closed)
- Item Catalog management (create/edit/delete)
- Model templates (save and reuse model setups)
- Model group templates (reuse common groups of models)
- Take-Off creation/editing for Project + Model Group
- Auto-generation of standard lines by stage based on business rules
- Manual overrides: add/remove/edit items and pricing
- Version snapshots (V1/V2/V3...) as immutable records; maintain a CURRENT working take-off
- PDF generation on demand with current company format
- Tax: fixed 7% rate, but taxable is per item/line (some items are NO TAX by agreement)
- Always apply Valve Discount (-112.99) before Grand Total

### Out of Scope (v2+)
- Upgrade automation (delta billing by area: Kitchen/Master/Secondary/Powder)
- Automatic diff view between versions (optional later)
- AI extraction from plan documents

## 3. Definitions
- **Project**: a community/job for a contractor (usually Lennar).
- **Model**: house/townhome/villa/condo model identifier (numbers/letters).
- **Model Group**: one take-off may cover multiple models if they are identical in items + quantities.
- **Stages**:
  - Ground
  - TopOut
  - Final
- **CURRENT**: editable take-off for active work.
- **Version**: immutable snapshot (V1, V2, V3...) created to preserve history.

## 4. Stakeholders
- Primary user: Karel (creates and maintains take-offs; uses them for invoicing and audits)
- Reviewer: Eric (validates proposal numbers before submission)
- External: Lennar (receives proposals; assigns item numbers; may request changes)

## 5. Functional Requirements

### FR-1 Projects
- Create project with:
  - project_name (required)
  - contractor_name (default: Lennar)
  - status (in_course/closed)
- Edit project fields
- List projects and open a project context for take-off creation

### FR-2 Item Catalog
- CRUD item catalog entries with:
  - internal_item_code (unique, required)
  - lennar_item_number (optional)
  - description1 (required)
  - description2 (optional)
  - unit (EA/LF/etc.)
  - item_type (material/service)
  - default_taxable (bool)
- Items must be usable in templates and take-offs
- Allow price edits (price is stored per takeoff line / template line, not globally fixed)

### FR-3 Templates (Model + Model Group)
- Create a model template (e.g., “1331”)
- Store default counts and default stage lines (including sort order)
- Load a model template into a take-off
- Create model group templates (sets of models commonly used together)
- Manage templates (rename, delete, avoid duplicates)

### FR-4 Take-Off (CURRENT)
- Create CURRENT take-off for project + model group
- Store:
  - model_group_display (string)
  - models list (JSON) for searching by individual model
  - stories (1–4)
  - counts (fixture_count float allowed, distances, etc.)
- Auto-generate standard stage lines
- Allow manual adjustments:
  - add new lines for special projects
  - edit qty, price, taxable flag, item numbers, descriptions
  - remove lines (with warning)

### FR-5 Versioning
- Create immutable snapshot versions: V1, V2, V3...
- Versions store all line details denormalized (prices never change)
- CURRENT remains editable and does not show “CURRENT” in filename when exported
- PDF generation is on-demand (not required on every save)

### FR-6 PDF Generation
- Generate PDF with:
  - company title and Created at date
  - table layout close to existing format
  - fixed ordering of lines per stage
  - stage totals (subtotal, tax, stage total)
  - grand totals and Valve Discount (-112.99) before Grand Total After Discount
- Remove the “%Tax” column (tax is fixed 7%); keep tax amount column

### FR-7 Water Heater Logic
- Support Tankless and Tank water heaters
- Auto-select correct install item based on heater type
- If multiple heaters, installation qty matches heater qty

### FR-8 Tax & Discount Rules
- TAX_RATE is fixed 7% (setting)
- Taxable is controlled per item/line (some material-like lines are NO TAX by agreement)
- Valve Discount is fixed at -112.99 for now (setting), applied before grand total after discount

## 6. Business Rules (summary)
See `docs/BusinessRules.md` for detailed rules.

## 7. Non-Functional Requirements
- Local-first: works offline
- Reliability: no data loss; versions immutable
- Auditability: created_at and notes on versions
- Maintainability: typed Python, clear module boundaries, tests
- Performance: PDF generation within seconds

## 8. Acceptance Criteria (MVP)
- Can create a project + take-off and generate a PDF matching the current structure and totals (within rounding conventions).
- Can save V1, continue editing CURRENT, save V2, and regenerate PDFs.
- Can change item prices in CURRENT and see totals update; older versions remain unchanged.
- Tax is calculated only on taxable lines; NO TAX lines remain untaxed even if they are “materials by name.”
- Valve Discount is applied consistently and visible in totals.
- Can search for a model inside a grouped take-off.
