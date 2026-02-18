from __future__ import annotations

from dataclasses import dataclass

from app.application.input_sources import TakeoffInputSource
from app.application.repositories.takeoff_repository import StoredTakeoff, TakeoffRepository
from app.application.resolve_takeoff import ResolveTakeoff
from app.application.save_takeoff import SaveTakeoff


@dataclass(frozen=True)
class SaveTakeoffFromInput:
    repo: TakeoffRepository

    def __call__(self, *, takeoff_input: TakeoffInputSource) -> StoredTakeoff:
        takeoff = ResolveTakeoff()(takeoff_input=takeoff_input)
        return SaveTakeoff(repo=self.repo)(takeoff)