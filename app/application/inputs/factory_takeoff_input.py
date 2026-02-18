from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.application.input_sources import TakeoffInputSource
from app.domain.takeoff import Takeoff


@dataclass(frozen=True)
class FactoryTakeoffInput(TakeoffInputSource):
    factory: Callable[[], Takeoff]

    def load(self, path: Path | None = None) -> Takeoff:
        # `path` is unused for factory-based inputs (kept for protocol compatibility)
        _ = path
        return self.factory()