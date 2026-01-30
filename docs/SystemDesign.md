# System Design — Take-Off App (Python)

## 1. Overview

Take-Off App is an internal application for Leza’s Plumbing to produce Take-Off PDFs used for:
- Submitting proposals to Lennar
- Billing by construction stage (Ground, TopOut, Final)
- Auditing payments against Lennar breakdowns
- Quickly identifying which fixtures/materials a specific Project + Model uses

The system is designed to be:
- Local-first (works without internet)
- Simple to operate for a small business
- Easy to extend (pricing policies, upgrades, AI extraction later)

## 2. Goals

### MVP (v1)
- Manage Projects
- Manage Item Catalog (create/edit/delete)
- Manage Templates (model templates + model group templates)
- Create/edit Take-Offs (CURRENT)
- Save version snapshots (V1, V2, V3...) as immutable records
- Generate Take-Off PDF matching the current company format
- Support fixed tax rate (7%) with per-item taxable flag (including “NO TAX by agreement” items)
- Always apply Valve Discount (-112.99) before Grand Total

### Future (v2+)
- Upgrade (delta) workflows by area (Kitchen / Master / Secondary / Powder)
- Version diff UI
- AI-assisted extraction from plumbing plans

## 3. Users

- Primary user: Karel (creates and maintains take-offs)
- Reviewer: Eric (reviews proposal numbers before submission)

## 4. System Context

### Inputs
- Manual counts derived from plans (fixture points, distances, tubs, hose bibbs, etc.)
- Item catalog data (internal stable item code, descriptions, unit, default taxable)
- Prices (editable at any time)
- Project status (in-course vs closed) for future price update automation

### Outputs
- Take-Off PDF by Project + Model Group
- Versioned snapshots (V1/V2/...) and a CURRENT working version in the database

## 5. Architecture Summary

### Application type
Local web app:
- UI: Streamlit (runs on the user’s machine)
- Database: SQLite
- PDF generation: ReportLab

### Layers (practical clean architecture)
- **domain/**: business entities + business rules (no UI, no DB)
- **application/**: use-cases (orchestrates domain logic)
- **infrastructure/**: SQLite repositories, PDF generator, file storage
- **ui/**: Streamlit pages and forms

This keeps business logic stable even if the UI changes later.

## 6. Key Business Rules (high level)

- Stages: Ground, TopOut, Final
- Split items (absolute): MAT’L PER FIXTURE, LABOR PER FIXTURE, DBL-BOWL VANITY
  - Ground factor: 0.30
  - TopOut factor: 0.30
  - Final factor: 0.40
- Stage-only items:
  - Ground-only: sewer/water line items, permit
  - TopOut-only: ice maker, hose bibb, bathtub items
  - Final-only: install services + finish fixtures and materials
- Tax rate is fixed at 7%, but taxable is controlled per item (some “materials” are NO TAX by agreement)
- Valve Discount is always applied as -112.99 before Grand Total
- Versioning:
  - CURRENT is editable
  - V1/V2/V3 are immutable snapshots

## 7. Data Flow (end-to-end)

1) Create Project
2) Create or select Model Group (optionally grouped models if identical)
3) Load a Template (preferred) or start from a generic template
4) Enter counts and exceptions
5) System generates lines for each stage using templates + rules
6) User edits/overrides lines as needed for special projects
7) Save snapshots (V1/V2/...) when changes must be preserved
8) Generate PDF on demand

## 8. UI Pages (Streamlit)

### 8.1 Projects
- Create/edit projects
- Track status (in-course/closed)

### 8.2 Items Catalog
- CRUD items
- Maintain internal stable item codes
- Maintain default taxable flag and item type metadata

### 8.3 Templates
- Model templates (per model)
- Model group templates (common sets of models)
- Admin tools: rename, merge, delete duplicates

### 8.4 Takeoffs
- Create takeoff from template
- Edit counts and lines
- Snapshot version (V1/V2/...)
- Generate PDF

## 9. PDF Generation Strategy

The PDF should match the existing company format as closely as possible:
- Title + company name
- Created at date
- A table per stage with fixed row ordering
- Stage totals (subtotal, tax, stage total)
- Grand totals + Valve Discount (-112.99) before final grand total

Implementation notes:
- Use ReportLab tables for predictable layout
- Remove the “%Tax” column (tax rate is always 7%)
- Keep a “Tax amount” column
- Store `sort_order` per line to preserve the same line sequence used today

## 10. Logging & Error Handling

- Use Python `logging` for:
  - invalid inputs
  - missing required counts
  - missing prices
  - PDF generation failures
- UI should show friendly messages while logs capture full details.

## 11. Testing Strategy

- Unit tests for:
  - stage factor rules (30/30/40)
  - tax calculation using taxable flags
  - valve discount
  - water heater install selection and quantities
- PDF tests:
  - generate a PDF and assert required text/totals exist (lightweight “golden” tests)
- Fixtures:
  - store sample input datasets (not necessarily the full PDF content)

## 12. Deployment & Storage

- Runs locally on Mac/Windows
- Repo stored in OneDrive for home/work usage
- Outputs stored in an `outputs/` folder (path configurable)

Risk note:
- Avoid opening the same SQLite DB simultaneously from two computers to prevent sync conflicts.
