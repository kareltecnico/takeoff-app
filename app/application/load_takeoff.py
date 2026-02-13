from __future__ import annotations

from dataclasses import dataclass

from app.application.repositories.takeoff_repository import TakeoffRepository
from app.domain.takeoff import Takeoff


@dataclass(frozen=True)
class LoadTakeoff:
    repo: TakeoffRepository

    def __call__(self, takeoff_id: str) -> Takeoff:
        return self.repo.load(takeoff_id)
