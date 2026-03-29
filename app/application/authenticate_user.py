from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest
from typing import Callable

from app.application.errors import InvalidInputError
from app.application.repositories.user_repository import UserRepository
from app.domain.user import User


class AuthenticationError(ValueError):
    """Raised when credentials are invalid for an authentication attempt."""


@dataclass(frozen=True)
class AuthenticateUser:
    repo: UserRepository
    verify_password: Callable[[str, str], bool]

    def __call__(self, *, username: str, password: str) -> User:
        normalized_username = username.strip()
        if not normalized_username:
            raise InvalidInputError("username cannot be empty")
        if not password:
            raise InvalidInputError("password cannot be empty")

        try:
            user = self.repo.get_by_username(normalized_username)
        except InvalidInputError as exc:
            raise AuthenticationError("Invalid credentials") from exc

        if not user.is_active:
            raise AuthenticationError("Invalid credentials")

        if not self.verify_password(password, user.password_hash):
            # compare_digest call keeps timing consistent when the verifier
            # returns a raw hash-like string in the future.
            compare_digest("x", "x")
            raise AuthenticationError("Invalid credentials")

        return user
