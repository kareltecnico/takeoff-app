# Roadmap — Take-Off App

## v1 (MVP) — Local app for take-off creation + PDF
- Projects page (create/edit, status)
- Items Catalog page (CRUD items)
- Templates page:
  - model templates (save/load)
  - model group templates
- Takeoffs page:
  - create from template
  - edit counts + line items
  - version snapshots (V1/V2/...)
  - generate PDF (ReportLab)
- Totals:
  - tax (7%, taxable per item)
  - valve discount (-112.99)
- Basic tests:
  - business rules math
  - PDF generation smoke tests

## v1.x — Plan-driven generation (Completed)
- Structured input (`PlanReadingInput`)
- Derived quantities layer
- Fixture mapping engine
- Project fixture overrides
- Line identity migration for duplicate items across stages
- Diff/report redesign using `mapping_id`
- CLI command for plan-driven takeoff generation

## v1.1 — Pricing policies for active project updates
Goal: reduce manual work when item prices change.
- Price lists with effective dates
- Project price policy (in-course projects can be updated automatically)
- Project overrides for rare “only these 2 projects” cases
- UI to apply a price update across selected projects

## v2 — Upgrades (delta) by area
- Support upgrade sets by area:
  - Kitchen / Master / Secondary / Powder
- Compute delta charges (upgrade minus standard)
- Optional “Upgrade Addendum” PDF
- Invoicing helper exports (optional)

## v3 — AI-assisted plan extraction (optional)
- Upload plumbing plan PDFs
- Extract fixture counts, tubs, etc. using AI
- Human review and corrections before generating take-off

## Future — Access Control (Role-based)
Goal: prevent accidental edits while allowing operational visibility.

Planned roles:

Editor / Admin
- Create projects
- Modify templates
- Create and edit take-offs
- Create snapshots
- Export revision bundles

Viewer / Read‑only
- Inspect projects
- View take-offs
- View snapshots
- Export reports

Notes:
- Intended for small team usage (owner + management + purchasing).
- Helps prevent accidental modification of production data.
- Authentication mechanism TBD (local users or simple credentials).
