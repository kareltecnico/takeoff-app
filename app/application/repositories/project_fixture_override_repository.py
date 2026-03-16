from __future__ import annotations

from typing import Protocol

from app.domain.fixture_mapping import ProjectFixtureOverride


class ProjectFixtureOverrideRepository(Protocol):
    def add(self, override: ProjectFixtureOverride) -> None: ...
    def get(self, *, project_code: str, mapping_id: str) -> ProjectFixtureOverride: ...
    def list_for_project(self, project_code: str) -> tuple[ProjectFixtureOverride, ...]: ...
