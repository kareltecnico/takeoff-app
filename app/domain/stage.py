from __future__ import annotations

from enum import Enum


class Stage(str, Enum):
    GROUND = "ground"
    TOPOUT = "topout"
    FINAL = "final"
