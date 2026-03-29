from __future__ import annotations

import sqlite3
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

from fastapi import Depends, Request, status

from app.application.authenticate_user import AuthenticateUser
from app.domain.user import User
from app.http.errors import raise_api_error
from app.http.security import verify_password
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_project_fixture_override_repository import (
    SqliteProjectFixtureOverrideRepository,
)
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_takeoff_line_repository import SqliteTakeoffLineRepository
from app.infrastructure.sqlite_takeoff_repository import SqliteTakeoffRepository
from app.infrastructure.sqlite_template_fixture_mapping_repository import (
    SqliteTemplateFixtureMappingRepository,
)
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository
from app.infrastructure.sqlite_user_repository import SqliteUserRepository


OFFICIAL_TEMPLATE_CODES = (
    "TH_STANDARD",
    "VILLA_1331",
    "VILLA_STANDARD",
    "SF_GENERIC",
)


@dataclass(frozen=True)
class RequestContext:
    conn: sqlite3.Connection
    projects: SqliteProjectRepository
    templates: SqliteTemplateRepository
    items: SqliteItemRepository
    takeoffs: SqliteTakeoffRepository
    takeoff_lines: SqliteTakeoffLineRepository
    template_mappings: SqliteTemplateFixtureMappingRepository
    project_overrides: SqliteProjectFixtureOverrideRepository
    users: SqliteUserRepository


def get_db(request: Request) -> Generator[sqlite3.Connection, None, None]:
    db_path = Path(request.app.state.db_path)
    conn = SqliteDb(path=db_path).connect()
    try:
        yield conn
    finally:
        conn.close()


def get_context(conn: sqlite3.Connection = Depends(get_db)) -> RequestContext:
    return RequestContext(
        conn=conn,
        projects=SqliteProjectRepository(conn=conn),
        templates=SqliteTemplateRepository(conn=conn),
        items=SqliteItemRepository(conn=conn),
        takeoffs=SqliteTakeoffRepository(conn=conn),
        takeoff_lines=SqliteTakeoffLineRepository(conn=conn),
        template_mappings=SqliteTemplateFixtureMappingRepository(conn=conn),
        project_overrides=SqliteProjectFixtureOverrideRepository(conn=conn),
        users=SqliteUserRepository(conn=conn),
    )


def get_authenticator(ctx: RequestContext = Depends(get_context)) -> AuthenticateUser:
    return AuthenticateUser(repo=ctx.users, verify_password=verify_password)


def get_current_user(
    request: Request,
    ctx: RequestContext = Depends(get_context),
) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise_api_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Authentication required.",
        )
    try:
        user = ctx.users.get_by_id(str(user_id))
    except Exception:
        raise_api_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Authentication required.",
        )
    if not user.is_active:
        raise_api_error(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Authentication required.",
        )
    return user


def require_editor(user: User = Depends(get_current_user)) -> User:
    if user.role != "editor":
        raise_api_error(
            status_code=status.HTTP_403_FORBIDDEN,
            code="forbidden",
            message="You do not have permission to perform this action.",
        )
    return user
