from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Template:
    code: str
    name: str
    category: str
    is_active: bool = True
