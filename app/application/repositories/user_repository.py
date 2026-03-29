from __future__ import annotations

from typing import Protocol

from app.domain.user import User


class UserRepository(Protocol):
    def get_by_id(self, user_id: str) -> User: ...

    def get_by_username(self, username: str) -> User: ...

    def upsert(self, user: User) -> None: ...
