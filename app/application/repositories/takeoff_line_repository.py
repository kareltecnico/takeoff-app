from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.takeoff_line_snapshot import TakeoffLineSnapshot


class TakeoffLineRepository(ABC):
    @abstractmethod
    def bulk_insert(self, lines: list[TakeoffLineSnapshot]) -> None: ...

    @abstractmethod
    def list_for_takeoff(self, takeoff_id: str) -> tuple[TakeoffLineSnapshot, ...]: ...
