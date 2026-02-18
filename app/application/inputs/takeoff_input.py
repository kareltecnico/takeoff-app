from __future__ import annotations

# Backwards-compatible alias:
# We keep this module because other code may import TakeoffInput from here.
from app.application.input_sources import TakeoffInputSource as TakeoffInput

__all__ = ["TakeoffInput"]