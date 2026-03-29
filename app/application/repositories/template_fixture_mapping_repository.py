from __future__ import annotations

from typing import Protocol

from app.domain.fixture_mapping import TemplateFixtureMappingRule


class TemplateFixtureMappingRepository(Protocol):
    def add(self, rule: TemplateFixtureMappingRule) -> None: ...
    def upsert(self, rule: TemplateFixtureMappingRule) -> None: ...
    def get(self, mapping_id: str) -> TemplateFixtureMappingRule: ...
    def list_for_template(
        self,
        template_code: str,
        *,
        include_inactive: bool = False,
    ) -> tuple[TemplateFixtureMappingRule, ...]: ...
    def set_active(self, mapping_id: str, *, is_active: bool) -> None: ...
