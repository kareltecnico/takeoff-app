from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.application.errors import InvalidInputError
from app.application.repositories.project_repository import ProjectRepository
from app.domain.project import Project


def _as_str(value: object, *, field: str) -> str:
    if isinstance(value, str):
        return value
    raise ValueError(f"Field {field!r} must be a string, got {type(value).__name__}")


def _as_opt_str(value: object | None, *, field: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ValueError(f"Field {field!r} must be a string or null, got {type(value).__name__}")


def _as_bool(value: object, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"Field {field!r} must be a bool, got {type(value).__name__}")


def _project_to_dict(p: Project) -> dict[str, object]:
    return {
        "code": p.code,
        "name": p.name,
        "contractor": p.contractor,
        "foreman": p.foreman,
        "is_active": p.is_active,
    }


def _project_from_dict(d: dict[str, object]) -> Project:
    return Project(
        code=_as_str(d.get("code"), field="code"),
        name=_as_str(d.get("name"), field="name"),
        contractor=_as_opt_str(d.get("contractor"), field="contractor"),
        foreman=_as_opt_str(d.get("foreman"), field="foreman"),
        is_active=_as_bool(d.get("is_active", True), field="is_active"),
    )


@dataclass(frozen=True)
class FileProjectRepository(ProjectRepository):
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_all({})

    def _read_all(self) -> dict[str, Project]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("Projects JSON must be a list")

        projects: dict[str, Project] = {}
        for row in raw:
            if not isinstance(row, dict):
                raise ValueError("Projects entries must be objects")
            row_typed: dict[str, object] = dict(row)
            p = _project_from_dict(row_typed)
            projects[p.code] = p
        return projects

    def _write_all(self, projects: dict[str, Project]) -> None:
        payload: list[dict[str, object]] = [_project_to_dict(p) for p in projects.values()]
        payload.sort(key=lambda x: str(x["code"]))

        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def upsert(self, project: Project) -> None:
        if not project.code.strip():
            raise InvalidInputError("Project.code cannot be empty")
        if not project.name.strip():
            raise InvalidInputError("Project.name cannot be empty")

        projects = self._read_all()
        projects[project.code] = project
        self._write_all(projects)

    def get(self, code: str) -> Project:
        projects = self._read_all()
        try:
            return projects[code]
        except KeyError as e:
            raise InvalidInputError(f"Project not found: {code}") from e

    def list(self, *, include_inactive: bool = False) -> tuple[Project, ...]:
        projects = self._read_all()
        vals = list(projects.values())
        if not include_inactive:
            vals = [p for p in vals if p.is_active]
        vals.sort(key=lambda p: p.code)
        return tuple(vals)

    def delete(self, code: str) -> None:
        projects = self._read_all()
        if code not in projects:
            raise InvalidInputError(f"Project not found: {code}")
        del projects[code]
        self._write_all(projects)
