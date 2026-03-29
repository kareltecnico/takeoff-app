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

## v1.x — Backend/API + Frontend MVP (Implemented Checkpoint)
- Frontend MVP specification documented in [FrontendMVP.md](./FrontendMVP.md)
- HTTP API bridge documented in [ApiMVP.md](./ApiMVP.md)
- FastAPI HTTP bridge implemented over existing application/use-case logic
- Simple cookie-session auth implemented with exactly two roles:
  - Editor
  - Viewer
- Official template selection for new takeoffs:
  - `TH_STANDARD`
  - `VILLA_1331`
  - `VILLA_STANDARD`
  - `SF_GENERIC`
- Legacy/provisional templates such as `TH_DEFAULT` stay out of normal baseline-selection UI
- Frontend slices completed:
  - login/session bootstrap
  - protected routing and role gating
  - projects list
  - create/generate takeoff flow
  - current takeoff detail
  - editor-only CURRENT line edit/delete
  - version history/detail and snapshot flow
  - export actions from current and version detail
- Item catalog/data model updates completed:
  - normalized approved baseline catalog
  - item category support in backend/data model
  - wrong legacy pedestal item `41FSPP0001` deactivated for future use
- Current known caveats:
  - create/generate item selectors now use the real catalog by category, but selected items do not yet drive backend generation
  - water-points override is still preview-only
  - premium/extra items and item creation modal are still deferred
  - export responses may still return a server-local file path rather than a dedicated browser download endpoint
  - Template Admin remains deferred in the frontend

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

## Future — Access Control Expansion
MVP role-based access is now approved in [FrontendMVP.md](./FrontendMVP.md).

Current MVP roles:

- Editor
- Viewer

Possible future expansion beyond MVP:

- broader admin/user management
- self-service password recovery
- more granular permissions
