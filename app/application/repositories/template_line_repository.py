from __future__ import annotations

from typing import Protocol

from app.domain.template_line import TemplateLine


class TemplateLineRepository(Protocol):
    def upsert(self, line: TemplateLine) -> None: ...
    def list_for_template(self, template_code: str) -> tuple[TemplateLine, ...]: ...
    def delete(self, template_code: str, item_code: str) -> None: ...
