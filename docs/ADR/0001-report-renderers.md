# ADR 0001 — Report DTO + Renderer Port (PDF/JSON/CSV)

## Status
Accepted

## Context
We need to generate multiple outputs (PDF now, JSON for debugging, CSV later) from the same Take-Off data.
Directly rendering from domain objects makes renderers complex and risks leaking domain rules into output code.
We also want the ability to add renderers without changing domain or use-case code.

## Decision
1. Introduce a reporting DTO (`TakeoffReport`) built from the domain `Takeoff`.
2. Introduce a renderer port:
   - `TakeoffReportRenderer` protocol with `render(report, output_path) -> Path`
3. Implement renderers in infrastructure:
   - ReportLab PDF renderer
   - JSON debug renderer
   - CSV renderer (future/now)

Additionally:
- In the reporting builder, clamp `grand_totals.total_after_discount` to never be negative in the final report output.

## Consequences
### Positive
- Domain remains pure and stable.
- Renderers are simple and consistent (work with the same DTO).
- Adding a new renderer requires only:
  - Create a new infrastructure file implementing the protocol.
  - Use it from a script/entrypoint.
- Testing becomes easier (DTO is deterministic).

### Trade-offs
- There is an extra “mapping” step (domain -> report DTO).
- Some formatting decisions move into reporting (e.g., clamping totals for display).

## Notes
- The use case name `GenerateTakeoffPdf` is kept for now for simplicity, but it effectively generates “report outputs” via injected renderer.
