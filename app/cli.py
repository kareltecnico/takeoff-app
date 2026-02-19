from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from app.application.build_sample_takeoff import BuildSampleTakeoff
from app.application.errors import InvalidInputError
from app.application.input_sources import TakeoffInputSource
from app.application.inputs.factory_takeoff_input import FactoryTakeoffInput
from app.application.inputs.json_takeoff_input import JsonTakeoffInput
from app.application.inputs.repo_takeoff_input import RepoTakeoffInput
from app.application.items_catalog import ItemsCatalog
from app.application.render_takeoff import RenderTakeoff
from app.config import AppConfig
from app.domain.output_format import OutputFormat
from app.infrastructure.file_item_repository import FileItemRepository
from app.infrastructure.file_takeoff_repository import FileTakeoffRepository
from app.infrastructure.renderer_registry import RendererRegistry
from app.application.projects import Projects
from app.infrastructure.file_project_repository import FileProjectRepository

# -----------------------------------
# Helpers
# -----------------------------------

def _require_non_empty(value: str | None, flag: str) -> str | None:
    if value is None:
        return None
    if not value.strip():
        raise SystemExit(f"{flag} cannot be empty")
    return value


def _parse_decimal(value: str, flag: str) -> Decimal:
    try:
        return Decimal(value)
    except Exception as e:
        raise SystemExit(f"Invalid {flag}: {value!r}") from e


def _validate_out_extension(fmt: OutputFormat, out: Path) -> None:
    expected = f".{fmt.value}"
    if out.suffix.lower() != expected:
        raise SystemExit(f"--out must end with {expected} for --format {fmt.value}")


def _parse_bool(value: str, flag: str) -> bool:
    v = value.strip().lower()
    if v in {"true", "1", "yes", "y", "on"}:
        return True
    if v in {"false", "0", "no", "n", "off"}:
        return False
    raise SystemExit(f"Invalid {flag}: {value!r} (use true/false)")


# -----------------------------------
# Validation
# -----------------------------------

def _validate_render_args(args: argparse.Namespace) -> None:
    fmt = OutputFormat(args.format)
    out = Path(args.out)
    _validate_out_extension(fmt, out)
    args.company_name = _require_non_empty(args.company_name, "--company-name")

    if args.id:
        if args.input != "sample" or args.input_path:
            raise SystemExit(
                "--id cannot be combined with --input/--input-path. "
                "Use either --id or --input ... (json/sample)."
            )

    if args.input == "json":
        if not args.input_path:
            raise SystemExit("--input-path is required when --input json is used")
        p = Path(args.input_path)
        if not p.exists():
            raise SystemExit(f"--input-path not found: {p}")
    else:
        if args.input_path:
            raise SystemExit("--input-path can only be used with --input json")

    if args.tax_rate:
        if args.input != "sample":
            raise SystemExit("--tax-rate is only allowed with --input sample")
        tr = _parse_decimal(args.tax_rate, "--tax-rate")
        if tr < Decimal("0") or tr > Decimal("1"):
            raise SystemExit("--tax-rate must be between 0 and 1")


def _validate_save_args(args: argparse.Namespace) -> None:
    repo_dir_raw = args.repo_dir
    if not repo_dir_raw or not str(repo_dir_raw).strip():
        raise SystemExit("--repo-dir cannot be empty")

    if args.input == "json":
        if not args.input_path:
            raise SystemExit("--input-path is required when --input json is used")
        p = Path(args.input_path)
        if not p.exists():
            raise SystemExit(f"--input-path not found: {p}")
    else:
        if args.input_path:
            raise SystemExit("--input-path can only be used with --input json")


# -----------------------------------
# Main
# -----------------------------------

def main(argv: list[str] | None = None) -> int:
    try:
        parser = argparse.ArgumentParser(prog="takeoff-app")
        sub = parser.add_subparsers(dest="cmd", required=True)

        # -------------------------
        # save
        # -------------------------
        save_parser = sub.add_parser("save")
        save_parser.add_argument("--input", choices=["sample", "json"], default="sample")
        save_parser.add_argument("--input-path", default=None)
        save_parser.add_argument("--repo-dir", default="data/takeoffs")

        # -------------------------
        # render
        # -------------------------
        render_parser = sub.add_parser("render")
        render_parser.add_argument("--input", choices=["sample", "json"], default="sample")
        render_parser.add_argument("--input-path", default=None)
        render_parser.add_argument("--id", default=None)
        render_parser.add_argument("--repo-dir", default="data/takeoffs")
        render_parser.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
        render_parser.add_argument("--out", required=True)
        render_parser.add_argument("--company-name", required=False)
        render_parser.add_argument("--tax-rate", required=False)

        # -------------------------
        # items (catalog)
        # -------------------------
        items_parser = sub.add_parser("items")
        items_sub = items_parser.add_subparsers(dest="items_cmd", required=True)
        items_parser.add_argument("--catalog-path", default="data/items_catalog.json")

        items_add = items_sub.add_parser("add")
        items_add.add_argument("--code", required=True)
        items_add.add_argument("--description", required=True)
        items_add.add_argument("--unit-price", required=True)
        items_add.add_argument("--taxable", required=True)  # true/false
        items_add.add_argument("--item-number", default=None)
        items_add.add_argument("--details", default=None)
        items_add.add_argument("--active", default="true")  # true/false

        items_list_parser = items_sub.add_parser("list")
        items_list_parser.add_argument("--include-inactive", action="store_true")

        items_get = items_sub.add_parser("get")
        items_get.add_argument("--code", required=True)

        items_update = items_sub.add_parser("update")
        items_update.add_argument("--code", required=True)
        items_update.add_argument("--description", default=None)
        items_update.add_argument("--unit-price", default=None)
        items_update.add_argument("--taxable", default=None)  # true/false
        items_update.add_argument("--item-number", default=None)
        items_update.add_argument("--details", default=None)
        items_update.add_argument("--active", default=None)  # true/false

        items_delete = items_sub.add_parser("delete")
        items_delete.add_argument("--code", required=True)

        # -------------------------
        # projects
        # -------------------------
        projects_parser = sub.add_parser("projects")
        projects_sub = projects_parser.add_subparsers(dest="projects_cmd", required=True)
        projects_parser.add_argument("--projects-path", default="data/projects.json")

        projects_add = projects_sub.add_parser("add")
        projects_add.add_argument("--code", required=True)
        projects_add.add_argument("--name", required=True)
        projects_add.add_argument("--contractor", default=None)
        projects_add.add_argument("--foreman", default=None)
        projects_add.add_argument("--active", default="true")  # true/false

        projects_list = projects_sub.add_parser("list")
        projects_list.add_argument("--include-inactive", action="store_true")

        projects_get = projects_sub.add_parser("get")
        projects_get.add_argument("--code", required=True)

        projects_update = projects_sub.add_parser("update")
        projects_update.add_argument("--code", required=True)
        projects_update.add_argument("--name", default=None)
        projects_update.add_argument("--contractor", default=None)
        projects_update.add_argument("--foreman", default=None)
        projects_update.add_argument("--active", default=None)  # true/false

        projects_delete = projects_sub.add_parser("delete")
        projects_delete.add_argument("--code", required=True)

        args = parser.parse_args(argv)
        
        # -------------------------
        # ITEMS HANDLER
        # -------------------------
        if args.cmd == "items":
            item_repo = FileItemRepository(path=Path(args.catalog_path))
            catalog = ItemsCatalog(repo=item_repo)

            if args.items_cmd == "add":
                catalog.add(
                    code=args.code,
                    description=args.description,
                    unit_price=_parse_decimal(args.unit_price, "--unit-price"),
                    taxable=_parse_bool(args.taxable, "--taxable"),
                    item_number=args.item_number,
                    details=args.details,
                    is_active=_parse_bool(args.active, "--active"),
                )
                print(f"Item saved: {args.code}")
                return 0

            if args.items_cmd == "list":
                item_list = catalog.list(include_inactive=args.include_inactive)
                if not item_list:
                    print("(no items)")
                    return 0
                for it in item_list:
                    active = "active" if it.is_active else "inactive"
                    tax = "taxable" if it.taxable else "non-taxable"
                    print(f"{it.code} | {it.description} | {it.unit_price} | {tax} | {active}")
                return 0

            if args.items_cmd == "get":
                it = catalog.get(code=args.code)
                print(f"code: {it.code}")
                print(f"item_number: {it.item_number}")
                print(f"description: {it.description}")
                print(f"details: {it.details}")
                print(f"unit_price: {it.unit_price}")
                print(f"taxable: {it.taxable}")
                print(f"is_active: {it.is_active}")
                return 0

            if args.items_cmd == "update":
                unit_price = None
                if args.unit_price is not None:
                    unit_price = _parse_decimal(args.unit_price, "--unit-price")

                taxable = None
                if args.taxable is not None:
                    taxable = _parse_bool(args.taxable, "--taxable")

                is_active = None
                if args.active is not None:
                    is_active = _parse_bool(args.active, "--active")

                catalog.update(
                    code=args.code,
                    description=args.description,
                    unit_price=unit_price,
                    taxable=taxable,
                    item_number=args.item_number,
                    details=args.details,
                    is_active=is_active,
                )
                print(f"Item updated: {args.code}")
                return 0

            if args.items_cmd == "delete":
                catalog.delete(code=args.code)
                print(f"Item deleted: {args.code}")
                return 0

            raise AssertionError("Unreachable: unknown items command")
        
        # -------------------------
        # PROJECTS HANDLER
        # -------------------------
        if args.cmd == "projects":
            project_repo = FileProjectRepository(path=Path(args.projects_path))
            projects = Projects(repo=project_repo)

            if args.projects_cmd == "add":
                projects.add(
                    code=args.code,
                    name=args.name,
                    contractor=args.contractor,
                    foreman=args.foreman,
                    is_active=_parse_bool(args.active, "--active"),
                )
                print(f"Project saved: {args.code}")
                return 0

            if args.projects_cmd == "list":
                project_list = projects.list(include_inactive=args.include_inactive)
                if not project_list:
                    print("(no projects)")
                    return 0
                for p in project_list:
                    active = "active" if p.is_active else "inactive"
                    print(f"{p.code} | {p.name} | contractor={p.contractor} | foreman={p.foreman} | {active}")
                return 0

            if args.projects_cmd == "get":
                p = projects.get(code=args.code)
                print(f"code: {p.code}")
                print(f"name: {p.name}")
                print(f"contractor: {p.contractor}")
                print(f"foreman: {p.foreman}")
                print(f"is_active: {p.is_active}")
                return 0

            if args.projects_cmd == "update":
                is_active = None
                if args.active is not None:
                    is_active = _parse_bool(args.active, "--active")

                projects.update(
                    code=args.code,
                    name=args.name,
                    contractor=args.contractor,
                    foreman=args.foreman,
                    is_active=is_active,
                )
                print(f"Project updated: {args.code}")
                return 0

            if args.projects_cmd == "delete":
                projects.delete(code=args.code)
                print(f"Project deleted: {args.code}")
                return 0

            raise AssertionError("Unreachable: unknown projects command")

        # -------------------------
        # takeoff repos/config (for save/render)
        # -------------------------
        takeoff_repo = FileTakeoffRepository(base_dir=Path(args.repo_dir))
        company_name = getattr(args, "company_name", None) or AppConfig().company_name
        config = AppConfig(company_name=company_name)
        sample_builder = BuildSampleTakeoff()

        # -------------------------
        # SAVE
        # -------------------------
        if args.cmd == "save":
            _validate_save_args(args)

            save_input: TakeoffInputSource
            if args.input == "json":
                save_input = JsonTakeoffInput(path=Path(args.input_path))
            else:
                save_input = FactoryTakeoffInput(factory=sample_builder)

            from app.application.save_takeoff_from_input import SaveTakeoffFromInput

            stored = SaveTakeoffFromInput(repo=takeoff_repo)(takeoff_input=save_input)
            print(f"SAVED takeoff id={stored.id} path={stored.path.resolve()}")
            return 0

        # -------------------------
        # RENDER
        # -------------------------
        if args.cmd == "render":
            _validate_render_args(args)

            fmt = OutputFormat(args.format)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)

            tax_override: Decimal | None = None
            if args.tax_rate:
                tax_override = _parse_decimal(args.tax_rate, "--tax-rate")

            takeoff_input: TakeoffInputSource
            if args.id:
                takeoff_input = RepoTakeoffInput(repo=takeoff_repo, takeoff_id=args.id)
            elif args.input == "json":
                takeoff_input = JsonTakeoffInput(path=Path(args.input_path))
            else:
                takeoff_input = FactoryTakeoffInput(factory=sample_builder)

            registry = RendererRegistry()

            rendered_path = RenderTakeoff(
                renderer_factory=registry,
                config=config,
            )(
                out=out,
                fmt=fmt,
                takeoff_input=takeoff_input,
                tax_rate_override=tax_override,
            )

            print(f"{fmt.value.upper()} generated at: {rendered_path.resolve()}")
            return 0

        raise AssertionError("Unreachable: unknown command")

    except InvalidInputError as e:
        print(str(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())