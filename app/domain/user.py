from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    user_id: str
    username: str
    display_name: str
    role: str
    password_hash: str
    is_active: bool = True
