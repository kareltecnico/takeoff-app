# Decisions Log (ADR-lite)

This file records key product and technical decisions with rationale.

## 2026-01-30 — App Type
**Decision:** Build a local web app using Streamlit.
**Rationale:** Fast to build, easy data entry UI, works locally, suitable for a small business.

## 2026-01-30 — Database
**Decision:** Use SQLite for MVP.
**Rationale:** Simple, local-first, easy backups, minimal ops.

## 2026-01-30 — PDF Generation
**Decision:** Use ReportLab for PDF generation.
**Rationale:** Precise control over table layout to match the existing take-off format.

## 2026-01-30 — Tax Handling
**Decision:** Tax rate is fixed at 7%, but taxability is controlled per item/line.
**Rationale:** Some lines are NO TAX by agreement even if they appear “material-like”.

## 2026-01-30 — Versioning
**Decision:** Maintain one editable CURRENT take-off and immutable snapshots V1/V2/...
**Rationale:** Preserve historical proposals for auditability and avoid rework.

## 2026-01-30 — Item Identity
**Decision:** Use `internal_item_code` as the stable unique key.
**Rationale:** Lennar item numbers can change; internal consistency is required.

## 2026-01-30 — Upgrades
**Decision:** Defer upgrades workflow to v2.
**Rationale:** Rare feature with higher complexity; MVP should focus on core take-off workflow first.

# Decisions

## 2026-02-09 — Introduce Reporting Layer (DTO + Renderer Port)
**Decision:** Add `app/reporting/` with:
- `TakeoffReport` DTO
- `TakeoffReportRenderer` port (Protocol)
- builder `build_takeoff_report()`

**Why:**
- Keep PDF generation free of domain logic.
- Make outputs pluggable (PDF, JSON, future HTML/CSV).
- Improve testability and maintainability.

## 2026-02-09 — Clamp negative totals in Reports (Option A)
**Decision:** In reporting builder, clamp `total_after_discount` to never be negative.

**Why:**
- Final displayed report should not show negative totals.
- Domain remains source of truth; report is presentation-safe.

## 2026-02-10 — Reporting layer and renderer ports

We introduced a dedicated Reporting layer with report DTOs and a renderer port (Protocol).

- Reporting DTOs: `TakeoffReport`, `ReportSection`, `ReportLine`, `ReportGrandTotals`
- Builder: `build_takeoff_report(takeoff, ...)`
- Renderer port: `TakeoffReportRenderer` (Protocol)
- Infrastructure adapters: ReportLab PDF renderer, JSON debug renderer, CSV renderer

Reason:
- Keep Domain pure and independent from I/O concerns.
- Enable multiple output formats without changing use cases.
- Make architecture easier to test and extend.

Decision:
- Use Option A ("clamp") in reporting: final `total_after_discount` is clamped to `0.00` for display.
