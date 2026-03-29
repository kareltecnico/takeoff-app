# Frontend MVP Specification — Take-Off App

## 1. Purpose

Build a clean, professional frontend for the Take-Off Generation System that allows:

- Editor users to create, generate, review, adjust, version, and export takeoffs
- Viewer users to open projects and review current and previous takeoffs in read-only mode

The frontend must reduce Excel-based manual work, not imitate Excel.

## 1.1 Current MVP Checkpoint

Implemented now:

- login + cookie-session bootstrap
- protected routes and exact two-role gating (`editor`, `viewer`)
- projects list
- current takeoff detail with grouped stage lines and totals summary
- editor-only create/generate takeoff flow
- editor-only CURRENT line edit/delete by `line_id`
- version history/detail and snapshot flow
- export actions from current takeoff and version detail
- Create / Generate page updated toward business workflow:
  - hidden/internal `project_code` generation
  - structure type, baseline/variant, and model entry flow
  - preview step before generate
  - explicit `Custom` path
  - real category-backed item selectors using the normalized catalog

Current caveats:

- selected items on the Create / Generate page are real catalog-backed selectors, but they do not yet change backend generation
- Water Points override is visible but still preview-only
- optional/premium item creation and persistence are deferred
- Template Admin is still deferred in the frontend
- export success may still surface a server-local file path until a dedicated download endpoint exists

This document remains the product specification source of truth. The checkpoint above records what is already implemented against that spec.

---

## 2. MVP Roles

### Editor

Can:

- log in
- create new project / takeoff
- select template during takeoff creation
- generate CURRENT takeoff from plan inputs
- inspect CURRENT lines
- update/delete CURRENT lines
- create revision/snapshot
- render/export
- access Template Admin

### Viewer

Can:

- log in
- search/open projects
- view CURRENT takeoff
- view revision history
- view version detail
- export/view rendered outputs if enabled

Cannot:

- create project
- generate takeoff
- edit/delete lines
- snapshot/revise
- access Template Admin

### Explicit MVP Rule

Viewer must not see mutation controls at all.

---

## 3. Authentication / Access

### MVP Decision

- Simple login only
- No guest access
- No advanced password reset UI
- No self-service forgot-password flow in MVP

### Access Behavior

- Editor uses normal login
- Viewer also uses normal login
- Password recovery is handled administratively / operationally outside MVP UI

---

## 4. Official Templates for MVP

Only these validated templates are part of the normal frontend creation flow:

- `TH_STANDARD`
- `VILLA_1331`
- `VILLA_STANDARD`
- `SF_GENERIC`

### Important Rule

Legacy/provisional templates such as `TH_DEFAULT` must not be used for new baseline validation and should not appear in the normal template selection UI.

---

## 5. Main Screens

### Screen 1 — Login

Purpose:

Authenticate user and start session.

UI elements:

- email/username
- password
- sign in button
- invalid-credentials error message

Out of MVP:

- guest access
- forgot password
- sign up
- advanced account management

### Screen 2 — Projects List

Purpose:

Main entry point after login.

Editor sees:

- searchable projects/takeoffs list
- status summary
- latest current takeoff summary
- `New Takeoff` button
- access to Template Admin
- quick links to Current, Versions, Exports

Viewer sees:

- searchable projects/takeoffs list
- status summary
- latest current takeoff summary
- quick links to Current, Versions, Exports
- no `New Takeoff` button
- no Template Admin access

Core UI components:

- top bar
- search/filter input
- project/takeoff table or cards
- status badges
- latest totals preview
- action buttons/links

### Screen 3 — Create Project / Takeoff

Purpose:

Editor-only flow to create or select a project and generate a new CURRENT takeoff.

Implemented direction:

- keep a clear split between existing-project and new-project paths
- hide `project_code` from the user and manage it internally
- use business-facing structure/baseline/model flow ahead of lower takeoff drivers
- keep an explicit `Custom` path rather than relying on no-template behavior

Current page structure:

Top flow:

- Structure Type
- Baseline / Variant when applicable
- Models

Project section:

- existing project selector
- or new project fields:
- project name
- contractor / builder
- foreman

Lower takeoff blocks:

- Core / Generated Drivers
- Standard Fixture Counts + Item Selection
- Auto-generated Operational Lines
- Optional / Premium / Extra Items

Current implementation notes:

- standard item selectors now load from the real catalog by category
- baseline defaults are preselected from frontend baseline config
- a Preview step exists before final generate/accept
- selected items are currently UI-level selections only and do not yet override backend generation

Output behavior:

On success:

- redirect to Current Takeoff Detail

Conflict behavior:

- if a CURRENT takeoff already exists for the same project/template pair, show a clear conflict message and offer navigation to the existing takeoff

### Screen 4 — Current Takeoff Detail

Purpose:

Main daily-use work screen.

Sections:

Header shows:

- project
- created/updated
- current/locked state

Do not show template used in normal project UI.

Totals summary shows:

- subtotal
- tax
- total

Current line table shows lines grouped by stage:

- Ground
- TopOut
- Final

Default visible columns:

- item code
- description
- qty
- stage
- factor
- sort order

Metadata handling:

- `line_id` is operational metadata
- do not make it a primary visible column for Viewer
- Editor may access it in edit flow or advanced details

Editor actions:

- edit line
- delete line
- snapshot / revise
- export / render
- refresh

Viewer actions:

- read-only view only
- export/view outputs if allowed
- no edit/delete/snapshot actions

### Screen 5 — Current Line Edit Modal

Purpose:

Editor-only mutation of CURRENT lines.

Show:

- line identity
- item code
- stage

Editable fields:

- qty
- stage
- factor
- sort order

Actions:

- `Save`
- `Delete`
- `Cancel`

Behavior:

- all line mutations must target by `line_id`
- Viewer never sees this modal

### Screen 6 — Version History

Purpose:

Review snapshots/revisions for a takeoff.

Show:

- revision list
- created date/time
- maybe totals summary
- open detail action

Access:

- Editor: read-only list + open version
- Viewer: same

No editing here.

### Screen 7 — Version Detail

Purpose:

Read-only view of a specific revision/snapshot.

Show:

- snapshot header
- grouped lines table
- subtotal / tax / total
- export action

Rule:

No editing in this screen for any role.

### Screen 8 — Export / Render

Purpose:

Access generated outputs.

MVP decision:

This does not need a separate full page unless required later.

It can live inside:

- Current Takeoff Detail
- Version Detail

Outputs:

- PDF
- CSV
- JSON if useful internally

### Screen 9 — Template Admin

Purpose:

Minimal Editor-only admin view for templates.

MVP scope:

Keep this very small.

Show:

- template list
- template metadata
- official / legacy status
- maybe mapping count

Do not build a large mapping editor UI in MVP unless it becomes necessary.

Access:

- Editor only
- not part of normal viewer/project flow

### Screen 10 — Profile / Session

Purpose:

Minimal session management.

Show:

- user name
- role
- sign out

Out of MVP:

- password reset UI
- profile editing
- advanced user settings

---

## 6. Navigation Flow

### Editor Flow

1. Login
2. Projects List
3. Create Project / Takeoff
4. Current Takeoff Detail
5. Current Line Edit Modal as needed
6. Version History
7. Version Detail
8. Export / Render

### Viewer Flow

1. Login
2. Projects List
3. Current Takeoff Detail
4. Version History
5. Version Detail
6. Export / Render if allowed

### Template Flow

- from top nav or editor menu
- open Template Admin
- separate from project detail

---

## 7. Role-Based UI Rules

### Editor

Can see:

- `New Takeoff`
- edit/delete line controls
- snapshot/revise controls
- Template Admin
- export controls

### Viewer

Can see:

- read-only project/takeoff information
- current and version history
- export controls if allowed

Must not see:

- `New Takeoff`
- `Edit`
- `Delete`
- `Snapshot`
- `Template Admin`
- any mutation control

---

## 8. Data / Backend Needs for Frontend MVP

Auth:

- login
- session/current user
- role information

Projects:

- list/search projects
- create project
- project detail

Templates:

- list active official templates
- fetch template metadata for admin

Takeoffs:

- generate from plan
- fetch current takeoff detail
- fetch current lines
- update line by `line_id`
- delete line by `line_id`
- revise/snapshot current takeoff
- list revisions
- fetch revision detail
- render/export

Totals:

- subtotal
- tax
- total

---

## 9. Visual Design Direction

Style:

- clean
- professional
- minimal
- readable
- operational

Guidance:

- light background
- restrained accent color
- clear cards/panels
- grouped tables
- strong spacing
- obvious buttons
- no visual clutter

The app should feel like a serious internal tool, not a decorative dashboard.

---

## 10. Recommended Implementation Order

1. Auth shell
- login
- session handling
- role gating
2. Projects List
- search/open path
- role-aware actions
3. Create Project / Takeoff
- select/create project
- select template
- enter plan inputs
- generate takeoff
4. Current Takeoff Detail
- grouped line table
- totals summary
- read-only first if needed
5. Editor line mutation
- edit/delete by `line_id`
6. Version History / Version Detail
- snapshot browsing
7. Snapshot / Revise action
- from Current Takeoff Detail
8. Export / Render surfaces
- current + versions
9. Template Admin
- minimal editor-only view

---

## 11. Explicitly Out of MVP

- guest access
- more than two roles
- forgot-password / self-service reset UI
- advanced user admin UI
- template visibility in normal viewer flow
- broad template editing UX
- spreadsheet-like Excel cloning UI
- tax as a default line-table column
- pricing history UI
- audit/event timeline UI
- AI extraction
- Excel import UX
- comments / approvals / notifications
- offline mode
- advanced dashboards
- auto-cascade behaviors

---

## 12. Final MVP Position

The Frontend MVP is approved to proceed once this document is treated as the working specification.

The HTTP bridge contract for this frontend is documented in [ApiMVP.md](./ApiMVP.md).

The frontend should be built around:

- simple login
- 2 roles
- project/takeoff workflow
- readable grouped takeoff views
- safe CURRENT editing by line
- version review
- export
