from __future__ import annotations

from dataclasses import dataclass

from app.application.errors import InvalidInputError
from app.domain.takeoff_line_snapshot import TakeoffLineSnapshot


@dataclass(frozen=True)
class ListTakeoffLines:
    repo: object

    def __call__(self, *, takeoff_id: str) -> tuple[TakeoffLineSnapshot, ...]:
        if not str(takeoff_id).strip():
            raise InvalidInputError("takeoff_id cannot be empty")

        return self.repo.list_for_takeoff(takeoff_id=takeoff_id)
