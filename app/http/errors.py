from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from app.application.authenticate_user import AuthenticationError
from app.application.errors import InvalidInputError


@dataclass(frozen=True)
class ApiError:
    status_code: int
    code: str
    message: str
    details: dict[str, Any] | None = None

    def to_http(self) -> HTTPException:
        payload: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            payload["error"]["details"] = self.details
        return HTTPException(status_code=self.status_code, detail=payload)


def raise_api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    raise ApiError(
        status_code=status_code,
        code=code,
        message=message,
        details=details,
    ).to_http()


def translate_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, AuthenticationError):
        return ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="invalid_credentials",
            message="Invalid username or password.",
        ).to_http()

    if not isinstance(exc, InvalidInputError):
        return ApiError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="bad_request",
            message=str(exc),
        ).to_http()

    message = str(exc)

    if message.startswith("Takeoff already exists for project="):
        details = {}
        for token in message.split():
            if token.startswith("project="):
                details["project_code"] = token.split("=", 1)[1]
            elif token.startswith("template="):
                details["template_code"] = token.split("=", 1)[1]
            elif token.startswith("id="):
                details["takeoff_id"] = token.split("=", 1)[1]
        return ApiError(
            status_code=status.HTTP_409_CONFLICT,
            code="current_takeoff_exists",
            message=message,
            details=details or None,
        ).to_http()

    if message.startswith("Takeoff generation produced no resolved lines"):
        return ApiError(
            status_code=status.HTTP_409_CONFLICT,
            code="no_resolved_lines",
            message=message,
        ).to_http()

    if message.startswith("Takeoff is locked:"):
        return ApiError(
            status_code=status.HTTP_409_CONFLICT,
            code="takeoff_locked",
            message=message,
        ).to_http()

    if message.startswith("Project is closed;"):
        return ApiError(
            status_code=status.HTTP_409_CONFLICT,
            code="project_closed",
            message=message,
        ).to_http()

    if message.startswith("Takeoff line not found:"):
        return ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="line_not_found",
            message=message,
        ).to_http()

    if message.startswith("Takeoff version not found:"):
        return ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=message,
        ).to_http()

    if (
        message.startswith("Project not found:")
        or message.startswith("Template not found:")
        or message.startswith("Takeoff not found:")
        or message.startswith("User not found:")
    ):
        return ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=message,
        ).to_http()

    if message in {
        "username cannot be empty",
        "password cannot be empty",
        "takeoff_id cannot be empty",
        "project_code cannot be empty",
        "template_code cannot be empty",
        "Provide exactly one of line_id or item_code",
        "At least one of qty, stage, factor, sort_order must be provided",
        "qty must be > 0",
        "factor must be > 0",
        "sort_order must be >= 0",
    }:
        return ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="validation_error",
            message=message,
        ).to_http()

    return ApiError(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message=message,
    ).to_http()
