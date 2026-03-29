from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.application.errors import InvalidInputError
from app.application.repositories.project_fixture_override_repository import (
    ProjectFixtureOverrideRepository,
)
from app.domain.fixture_mapping import ProjectFixtureOverride


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
class SqliteProjectFixtureOverrideRepository(ProjectFixtureOverrideRepository):
    conn: sqlite3.Connection

    def _validate_override(self, override: ProjectFixtureOverride) -> None:
        if not override.project_code.strip():
            raise InvalidInputError("ProjectFixtureOverride.project_code cannot be empty")
        if not override.mapping_id.strip():
            raise InvalidInputError("ProjectFixtureOverride.mapping_id cannot be empty")

    def add(self, override: ProjectFixtureOverride) -> None:
        self._validate_override(override)

        try:
            self.conn.execute(
                """
                INSERT INTO project_fixture_overrides (
                    project_code,
                    mapping_id,
                    is_disabled,
                    item_code_override,
                    notes_override,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    override.project_code,
                    override.mapping_id,
                    _b(override.is_disabled),
                    override.item_code_override,
                    override.notes_override,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise InvalidInputError(
                "Project fixture override constraint failed "
                f"(project_code={override.project_code!r}, mapping_id={override.mapping_id!r})"
            ) from exc

        self.conn.commit()

    def upsert(self, override: ProjectFixtureOverride) -> None:
        self._validate_override(override)

        try:
            self.conn.execute(
                """
                INSERT INTO project_fixture_overrides (
                    project_code,
                    mapping_id,
                    is_disabled,
                    item_code_override,
                    notes_override,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(project_code, mapping_id) DO UPDATE SET
                    is_disabled=excluded.is_disabled,
                    item_code_override=excluded.item_code_override,
                    notes_override=excluded.notes_override,
                    updated_at=datetime('now')
                """,
                (
                    override.project_code,
                    override.mapping_id,
                    _b(override.is_disabled),
                    override.item_code_override,
                    override.notes_override,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise InvalidInputError(
                "Project fixture override constraint failed "
                f"(project_code={override.project_code!r}, mapping_id={override.mapping_id!r})"
            ) from exc

        self.conn.commit()

    def get(self, *, project_code: str, mapping_id: str) -> ProjectFixtureOverride:
        row = self.conn.execute(
            """
            SELECT
                project_code,
                mapping_id,
                is_disabled,
                item_code_override,
                notes_override
            FROM project_fixture_overrides
            WHERE project_code = ? AND mapping_id = ?
            """,
            (project_code, mapping_id),
        ).fetchone()

        if row is None:
            raise InvalidInputError(
                f"Project fixture override not found: {project_code} / {mapping_id}"
            )

        return ProjectFixtureOverride(
            project_code=str(row["project_code"]),
            mapping_id=str(row["mapping_id"]),
            is_disabled=_bool(row["is_disabled"]),
            item_code_override=row["item_code_override"],
            notes_override=row["notes_override"],
        )

    def list_for_project(self, project_code: str) -> tuple[ProjectFixtureOverride, ...]:
        rows = self.conn.execute(
            """
            SELECT
                project_code,
                mapping_id,
                is_disabled,
                item_code_override,
                notes_override
            FROM project_fixture_overrides
            WHERE project_code = ?
            ORDER BY mapping_id
            """,
            (project_code,),
        ).fetchall()

        return tuple(
            ProjectFixtureOverride(
                project_code=str(row["project_code"]),
                mapping_id=str(row["mapping_id"]),
                is_disabled=_bool(row["is_disabled"]),
                item_code_override=row["item_code_override"],
                notes_override=row["notes_override"],
            )
            for row in rows
        )

    def delete(self, *, project_code: str, mapping_id: str) -> None:
        cur = self.conn.execute(
            """
            DELETE FROM project_fixture_overrides
            WHERE project_code = ? AND mapping_id = ?
            """,
            (project_code, mapping_id),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            raise InvalidInputError(
                f"Project fixture override not found: {project_code} / {mapping_id}"
            )
