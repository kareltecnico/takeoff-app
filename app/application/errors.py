from __future__ import annotations


class InvalidInputError(ValueError):
    """Raised when user-provided input is invalid for a use case."""


class AccessDeniedError(PermissionError):
    """Raised when an action is not allowed for the active user role."""
