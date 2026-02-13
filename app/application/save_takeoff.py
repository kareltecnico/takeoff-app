from __future__ import annotations

from dataclasses import dataclass

from app.application.repositories.takeoff_repository import StoredTakeoff, TakeoffRepository
from app.domain.takeoff import Takeoff


@dataclass(frozen=True)
class SaveTakeoff:
    repo: TakeoffRepository

    def __call__(self, takeoff: Takeoff) -> StoredTakeoff:
        return self.repo.save(takeoff)
