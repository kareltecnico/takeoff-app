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
