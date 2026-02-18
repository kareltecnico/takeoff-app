from __future__ import annotations

from dataclasses import dataclass

from app.application.input_sources import TakeoffInputSource
from app.domain.takeoff import Takeoff


@dataclass(frozen=True)
class ResolveTakeoff:
    """Resolve a Takeoff from a given input source.

    This use case is intentionally dumb: it delegates the loading/building
    logic to the input object (polymorphism), so we avoid flags/conditionals
    and keep the application layer clean.
    """

    def __call__(self, *, takeoff_input: TakeoffInputSource) -> Takeoff:
        return takeoff_input.load()