from __future__ import annotations

# Backwards-compatible alias.
# Reporting should not depend on concrete infrastructure implementations.
from app.infrastructure.renderer_registry import RendererRegistry

__all__ = ["RendererRegistry"]