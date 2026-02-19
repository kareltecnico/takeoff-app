from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    code: str
    name: str
    contractor: str | None = None
    foreman: str | None = None
    is_active: bool = True
