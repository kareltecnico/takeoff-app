from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.domain.takeoff import Takeoff


class TakeoffInput(Protocol):
    def load(self, path: Path | None = None) -> Takeoff: ...
