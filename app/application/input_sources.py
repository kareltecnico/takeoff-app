from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.domain.takeoff import Takeoff


class TakeoffInputSource(Protocol):
    """Port for producing a domain Takeoff.

    Some sources need a path (e.g., JSON file). Others are built-in (sample).
    """

    def load(self, path: Path | None = None) -> Takeoff: ...