from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.application.repositories.project_repository import ProjectRepository
from app.domain.project import Project


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
class SqliteProjectRepository(ProjectRepository):
    conn: sqlite3.Connection

    def upsert(self, project: Project) -> None:
        if not project.code.strip():
            raise InvalidInputError("Project.code cannot be empty")
        if not project.name.strip():
            raise InvalidInputError("Project.name cannot be empty")

        self.conn.execute(
            """
            INSERT INTO projects (
                project_code,
                project_name,
                contractor_name,
                foreman,
                valve_discount,
                is_active,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(project_code) DO UPDATE SET
                project_name=excluded.project_name,
                contractor_name=excluded.contractor_name,
                foreman=excluded.foreman,
                valve_discount=excluded.valve_discount,
                is_active=excluded.is_active,
                updated_at=datetime('now')
            """,
            (
                project.code,
                project.name,
                project.contractor,
                project.foreman,
                str(project.valve_discount),
                _b(project.is_active),
            ),
        )
        self.conn.commit()

    def get(self, code: str) -> Project:
        
        row = self.conn.execute(
            """
            SELECT project_code, project_name, contractor_name, foreman, is_active, valve_discount
            FROM projects
            WHERE project_code = ?
            """,
            (code,),
        ).fetchone()

        if row is None:
            raise InvalidInputError(f"Project not found: {code}")

        return Project(
            code=str(row["project_code"]),
            name=str(row["project_name"]),
            contractor=row["contractor_name"],
            foreman=row["foreman"],
            is_active=_bool(row["is_active"]),
            valve_discount=Decimal(str(row["valve_discount"])),
        )

    def list(self, *, include_inactive: bool = False) -> tuple[Project, ...]:
        
        if include_inactive:
            rows = self.conn.execute(
                """
                SELECT project_code, project_name, contractor_name, foreman, is_active, valve_discount
                FROM projects
                ORDER BY project_code
                """
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT project_code, project_name, contractor_name, foreman, is_active, valve_discount
                FROM projects
                WHERE is_active = 1
                ORDER BY project_code
                """
            ).fetchall()

        out: list[Project] = []
        for row in rows:
            out.append(
                Project(
                    code=str(row["project_code"]),
                    name=str(row["project_name"]),
                    contractor=row["contractor_name"],
                    foreman=row["foreman"],
                    is_active=_bool(row["is_active"]),
                    valve_discount=Decimal(str(row["valve_discount"])),
                )
            )
        return tuple(out)
    
    def set_valve_discount(self, code: str, *, valve_discount: Decimal) -> None:
        if not str(code).strip():
            raise InvalidInputError("Project code cannot be empty")

        # Validate existence (and raise clean error if missing)
        _ = self.get(code=code)

        self.conn.execute(
            """
            UPDATE projects
            SET valve_discount = ?, updated_at = datetime('now')
            WHERE project_code = ?
            """,
            (str(valve_discount), code),
        )
        self.conn.commit()

    def delete(self, code: str) -> None:
        cur = self.conn.execute(
            "DELETE FROM projects WHERE project_code = ?",
            (code,),
        )
        self.conn.commit()
        if cur.rowcount == 0:
            raise InvalidInputError(f"Project not found: {code}")