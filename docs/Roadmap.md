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
