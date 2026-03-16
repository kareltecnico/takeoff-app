# AGENTS.md

Source of truth:
- docs/SRS.md
- docs/BusinessRules.md
- docs/SystemDesign.md
- docs/Decisions.md
- README.md

Project rules:
- Do not redesign architecture
- Do not rename files unless necessary
- Follow the documented roadmap only
- Ask before assuming unclear business rules
- Keep changes minimal and scoped
- Do not touch unrelated files
- Run tests after each meaningful change

Testing:
- Run: pytest -q

Current pipeline:
PlanReadingInput
-> DerivedQuantities
-> TemplateFixtureMapping
-> ProjectFixtureOverride
-> TakeoffLines
-> PDF Rendering
