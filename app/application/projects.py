from __future__ import annotations

from dataclasses import dataclass

from app.application.errors import InvalidInputError
from app.application.repositories.project_repository import ProjectRepository
from app.domain.project import Project


@dataclass(frozen=True)
class Projects:
    repo: ProjectRepository

    def add(
        self,
        *,
        code: str,
        name: str,
        contractor: str | None = None,
        foreman: str | None = None,
        is_active: bool = True,
    ) -> None:
        code = code.strip()
        name = name.strip()

        if not code:
            raise InvalidInputError("--code cannot be empty")
        if not name:
            raise InvalidInputError("--name cannot be empty")

        self.repo.upsert(
            Project(
                code=code,
                name=name,
                contractor=contractor.strip() if contractor is not None else None,
                foreman=foreman.strip() if foreman is not None else None,
                is_active=is_active,
            )
        )

    def get(self, *, code: str) -> Project:
        return self.repo.get(code)

    def list(self, *, include_inactive: bool = False) -> tuple[Project, ...]:
        return self.repo.list(include_inactive=include_inactive)

    def update(
        self,
        *,
        code: str,
        name: str | None = None,
        contractor: str | None = None,
        foreman: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        current = self.repo.get(code)

        new_name = current.name if name is None else name.strip()
        if not new_name:
            raise InvalidInputError("--name cannot be empty")

        self.repo.upsert(
            Project(
                code=current.code,
                name=new_name,
                contractor=current.contractor if contractor is None else contractor.strip(),
                foreman=current.foreman if foreman is None else foreman.strip(),
                is_active=current.is_active if is_active is None else is_active,
            )
        )

    def delete(self, *, code: str) -> None:
        self.repo.delete(code)
