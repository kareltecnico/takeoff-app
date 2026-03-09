from __future__ import annotations

from dataclasses import dataclass

from app.application.errors import InvalidInputError


@dataclass(frozen=True)
class DeleteTakeoffLine:
    repo: object

    def __call__(self, *, takeoff_id: str, item_code: str) -> None:
        if not str(takeoff_id).strip():
            raise InvalidInputError("takeoff_id cannot be empty")
        if not str(item_code).strip():
            raise InvalidInputError("item_code cannot be empty")

        self.repo.delete_line(
            takeoff_id=takeoff_id,
            item_code=item_code,
        )
