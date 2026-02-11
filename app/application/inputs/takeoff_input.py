from __future__ import annotations

from typing import Protocol

from app.domain.takeoff import Takeoff


class TakeoffInput(Protocol):
    def load(self) -> Takeoff: ...
