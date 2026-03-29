from __future__ import annotations

from dataclasses import dataclass

from app.application.errors import InvalidInputError


@dataclass(frozen=True)
class DeleteTakeoffLine:
    repo: object

    def __call__(
        self,
        *,
        takeoff_id: str,
        line_id: str | None = None,
        item_code: str | None = None,
    ) -> None:
        if not str(takeoff_id).strip():
            raise InvalidInputError("takeoff_id cannot be empty")
        has_line_id = bool(str(line_id or "").strip())
        has_item_code = bool(str(item_code or "").strip())
        if has_line_id == has_item_code:
            raise InvalidInputError("Provide exactly one of line_id or item_code")

        self.repo.delete_line(
            line_id=line_id,
            takeoff_id=takeoff_id,
            item_code=item_code,
        )
