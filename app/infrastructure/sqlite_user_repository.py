from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.application.errors import InvalidInputError
from app.application.repositories.user_repository import UserRepository
from app.domain.user import User


def _b(value: bool) -> int:
    return 1 if value else 0


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, (str, bytes, bytearray)):
        return int(value) != 0
    raise TypeError(f"Expected boolean-ish SQLite value, got {type(value).__name__}")


@dataclass(frozen=True)
class SqliteUserRepository(UserRepository):
    conn: sqlite3.Connection

    def get_by_id(self, user_id: str) -> User:
        row = self.conn.execute(
            """
            SELECT user_id, username, display_name, role, password_hash, is_active
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            raise InvalidInputError(f"User not found: {user_id}")
        return User(
            user_id=str(row["user_id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            role=str(row["role"]),
            password_hash=str(row["password_hash"]),
            is_active=_bool(row["is_active"]),
        )

    def get_by_username(self, username: str) -> User:
        row = self.conn.execute(
            """
            SELECT user_id, username, display_name, role, password_hash, is_active
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
        if row is None:
            raise InvalidInputError(f"User not found: {username}")
        return User(
            user_id=str(row["user_id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            role=str(row["role"]),
            password_hash=str(row["password_hash"]),
            is_active=_bool(row["is_active"]),
        )

    def upsert(self, user: User) -> None:
        self.conn.execute(
            """
            INSERT INTO users (
                user_id,
                username,
                display_name,
                role,
                password_hash,
                is_active,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                display_name=excluded.display_name,
                role=excluded.role,
                password_hash=excluded.password_hash,
                is_active=excluded.is_active,
                updated_at=datetime('now')
            """,
            (
                user.user_id,
                user.username,
                user.display_name,
                user.role,
                user.password_hash,
                _b(user.is_active),
            ),
        )
        self.conn.commit()
