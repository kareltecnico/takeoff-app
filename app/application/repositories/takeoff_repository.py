from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.domain.takeoff import Takeoff


@dataclass(frozen=True)
class StoredTakeoff:
    id: str
    path: Path


class TakeoffRepository(Protocol):
    def save(self, takeoff: Takeoff) -> StoredTakeoff: ...
    def load(self, takeoff_id: str) -> Takeoff: ...
