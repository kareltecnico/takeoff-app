from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.application.errors import InvalidInputError
from app.application.repositories.item_repository import ItemRepository
from app.application.repositories.template_line_repository import TemplateLineRepository
from app.application.repositories.template_repository import TemplateRepository
from app.domain.template import Template
from app.domain.template_line import TemplateLine


@dataclass(frozen=True)
class Templates:
    templates_repo: TemplateRepository
    lines_repo: TemplateLineRepository
    items_repo: ItemRepository  # to validate item exists

    def add(self, *, code: str, name: str, category: str, is_active: bool = True) -> None:
        self.templates_repo.upsert(
            Template(code=code, name=name, category=category, is_active=is_active)
        )

    def update(
        self,
        *,
        code: str,
        name: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        current = self.templates_repo.get(code)
        self.templates_repo.upsert(
            Template(
                code=current.code,
                name=name if name is not None else current.name,
                category=category if category is not None else current.category,
                is_active=is_active if is_active is not None else current.is_active,
            )
        )

    def get(self, *, code: str) -> Template:
        return self.templates_repo.get(code)

    def list(self, *, include_inactive: bool = False) -> tuple[Template, ...]:
        return self.templates_repo.list(include_inactive=include_inactive)

    def delete(self, *, code: str) -> None:
        self.templates_repo.delete(code)

    # -------------------------
    # Lines
    # -------------------------
    def add_line(
        self,
        *,
        template_code: str,
        item_code: str,
        qty: Decimal,
        notes: str | None = None,
    ) -> None:
        # Validate template exists
        _ = self.templates_repo.get(template_code)

        # Validate item exists
        try:
            _ = self.items_repo.get(item_code)
        except Exception as e:
            raise InvalidInputError(f"Item not found: {item_code}") from e

        self.lines_repo.upsert(
            TemplateLine(
                template_code=template_code,
                item_code=item_code,
                qty=qty,
                notes=notes,
            )
        )

    def list_lines(self, *, template_code: str) -> tuple[TemplateLine, ...]:
        # Validate template exists
        _ = self.templates_repo.get(template_code)
        return self.lines_repo.list_for_template(template_code)

    def remove_line(self, *, template_code: str, item_code: str) -> None:
        self.lines_repo.delete(template_code, item_code)
