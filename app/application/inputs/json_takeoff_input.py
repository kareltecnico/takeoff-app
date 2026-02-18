from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.application.errors import InvalidInputError
from app.application.input_sources import TakeoffInputSource
from app.domain.takeoff import Takeoff
from app.infrastructure.takeoff_json_loader import TakeoffJsonLoader


@dataclass(frozen=True)
class JsonTakeoffInput(TakeoffInputSource):
    path: Path
    loader: TakeoffJsonLoader = TakeoffJsonLoader()

    def load(self, path: Path | None = None) -> Takeoff:
        # ignore method arg; use the path captured in the object
        if not self.path:
            raise InvalidInputError("JSON input requires --input-path")

        return self.loader.load(self.path)