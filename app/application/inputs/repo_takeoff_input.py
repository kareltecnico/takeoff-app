from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.application.errors import InvalidInputError
from app.application.input_sources import TakeoffInputSource
from app.application.load_takeoff import LoadTakeoff
from app.application.repositories.takeoff_repository import TakeoffRepository
from app.domain.takeoff import Takeoff


@dataclass(frozen=True)
class RepoTakeoffInput(TakeoffInputSource):
    repo: TakeoffRepository
    takeoff_id: str

    def load(self, path: Path | None = None) -> Takeoff:
        # `path` is unused for repo-based inputs (kept for protocol compatibility)
        _ = path

        if not self.takeoff_id or not str(self.takeoff_id).strip():
            raise InvalidInputError("--id cannot be empty")

        return LoadTakeoff(repo=self.repo)(self.takeoff_id)