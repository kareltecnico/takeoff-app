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
from app.application.render_takeoff import RenderTakeoff
from app.application.render_takeoff_from_snapshot import RenderTakeoffFromSnapshot
from app.application.save_takeoff import SaveTakeoff
from app.application.seed_takeoff_from_template import SeedTakeoffFromTemplate
from app.config import AppConfig
from app.domain.output_format import OutputFormat
from app.domain.project import Project
from app.infrastructure.file_takeoff_repository import FileTakeoffRepository
from app.infrastructure.renderer_registry import RendererRegistry
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_takeoff_line_repository import SqliteTakeoffLineRepository
from app.infrastructure.sqlite_takeoff_repository import SqliteTakeoffRepository
from app.infrastructure.sqlite_template_line_repository import SqliteTemplateLineRepository
from app.infrastructure.sqlite_template_repository import SqliteTemplateRepository
from app.infrastructure.takeoff_json_loader import TakeoffJsonLoader

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

        # Global (SQLite)
        parser.add_argument("--db-path", default="data/takeoff.db")

        sub = parser.add_subparsers(dest="cmd", required=True)

        # -------------------------
        # save (file repo)
        # -------------------------
        save = sub.add_parser("save")
        save.add_argument("--input", choices=["sample", "json"], default="sample")
        save.add_argument("--input-path", default=None)
        save.add_argument("--repo-dir", default="data/takeoffs")

        # -------------------------
        # render (file repo)
        # -------------------------
        render = sub.add_parser("render")
        render.add_argument("--input", choices=["sample", "json"], default="sample")
        render.add_argument("--input-path", default=None)
        render.add_argument("--id", default=None)
        render.add_argument("--repo-dir", default="data/takeoffs")
        render.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
        render.add_argument("--out", required=True)
        render.add_argument("--company-name", required=False)
        render.add_argument("--tax-rate", required=False)

        # -------------------------
        # projects (SQLite)
        # -------------------------
        projects = sub.add_parser("projects")
        projects_sub = projects.add_subparsers(dest="projects_cmd", required=True)

        p_add = projects_sub.add_parser("add")
        p_add.add_argument("--code", required=True)
        p_add.add_argument("--name", required=True)
        p_add.add_argument("--contractor", required=True)
        p_add.add_argument("--foreman", required=True)
        p_add.add_argument("--inactive", action="store_true")

        p_list = projects_sub.add_parser("list")
        p_list.add_argument("--all", action="store_true", help="Include inactive projects")

        p_show = projects_sub.add_parser("show")
        p_show.add_argument("--code", required=True)

        p_del = projects_sub.add_parser("delete")
        p_del.add_argument("--code", required=True)

        # -------------------------
        # takeoffs (SQLite)
        # -------------------------
        takeoffs = sub.add_parser("takeoffs")
        takeoffs_sub = takeoffs.add_subparsers(dest="takeoffs_cmd", required=True)

        seed = takeoffs_sub.add_parser("seed")
        seed.add_argument("--project", required=True)
        seed.add_argument("--template", required=True)
        seed.add_argument("--tax-rate", required=False)

        lst = takeoffs_sub.add_parser("list")
        lst.add_argument("--project", required=True)

        show = takeoffs_sub.add_parser("show")
        show.add_argument("--id", required=True)

        rnd = takeoffs_sub.add_parser("render")
        rnd.add_argument("--id", required=True)
        rnd.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
        rnd.add_argument("--out", required=True)

        args = parser.parse_args(argv)

        # File repo (existing)
        file_repo = FileTakeoffRepository(base_dir=Path(getattr(args, "repo_dir", "data/takeoffs")))
        company_name = getattr(args, "company_name", None) or AppConfig().company_name
        config = AppConfig(company_name=company_name)
        sample_builder = BuildSampleTakeoff()

        # -------------------------
        # SAVE
        # -------------------------
        if args.cmd == "save":
            _validate_save_args(args)

            if args.input == "json":
                takeoff = TakeoffJsonLoader().load(Path(args.input_path))
            else:
                takeoff = sample_builder()

            stored = SaveTakeoff(repo=file_repo)(takeoff)
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
                takeoff_input = RepoTakeoffInput(repo=file_repo, takeoff_id=args.id)
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

        # -------------------------
        # PROJECTS (SQLite)
        # -------------------------
        if args.cmd == "projects":
            conn = SqliteDb(path=Path(args.db_path)).connect()
            try:
                project_repo = SqliteProjectRepository(conn=conn)

                if args.projects_cmd == "add":
                    project_repo.upsert(
                        Project(
                            code=args.code,
                            name=args.name,
                            contractor=args.contractor,
                            foreman=args.foreman,
                            is_active=not args.inactive,
                        )
                    )
                    status = "inactive" if args.inactive else "active"
                    print(f"PROJECT saved code={args.code} status={status}")
                    return 0

                if args.projects_cmd == "list":
                    rows = project_repo.list(include_inactive=bool(args.all))
                    for p in rows:
                        active = "active" if p.is_active else "inactive"
                        print(
                            f"{p.code} | {p.name} | contractor={p.contractor} | "
                            f"foreman={p.foreman} | {active}"
                        )
                    return 0

                if args.projects_cmd == "show":
                    p = project_repo.get(code=args.code)
                    active = "active" if p.is_active else "inactive"
                    print(
                        f"{p.code} | {p.name} | contractor={p.contractor} | "
                        f"foreman={p.foreman} | {active}"
                    )
                    return 0

                if args.projects_cmd == "delete":
                    project_repo.delete(code=args.code)
                    print(f"PROJECT deleted code={args.code}")
                    return 0

                raise AssertionError("Unreachable: unknown projects command")

            finally:
                conn.close()

        # -------------------------
        # TAKEOFFS (SQLite)
        # -------------------------
        if args.cmd == "takeoffs":
            conn = SqliteDb(path=Path(args.db_path)).connect()
            try:
                item_repo = SqliteItemRepository(conn=conn)
                project_repo = SqliteProjectRepository(conn=conn)
                template_repo = SqliteTemplateRepository(conn=conn)
                template_line_repo = SqliteTemplateLineRepository(conn=conn)
                takeoff_repo = SqliteTakeoffRepository(conn=conn)
                takeoff_line_repo = SqliteTakeoffLineRepository(conn=conn)

                if args.takeoffs_cmd == "seed":
                    tax_rate: Decimal | None = None
                    if args.tax_rate:
                        tax_rate = _parse_decimal(args.tax_rate, "--tax-rate")

                    use_case = SeedTakeoffFromTemplate(
                        project_repo=project_repo,
                        template_repo=template_repo,
                        template_line_repo=template_line_repo,
                        item_repo=item_repo,
                        takeoff_repo=takeoff_repo,
                        takeoff_line_repo=takeoff_line_repo,
                    )

                    takeoff_id = use_case(
                        project_code=args.project,
                        template_code=args.template,
                        tax_rate_override=tax_rate,
                    )

                    print(
                        f"TAKEOFF seeded id={takeoff_id} "
                        f"project={args.project} template={args.template}"
                    )
                    return 0

                if args.takeoffs_cmd == "list":
                    rows = takeoff_repo.list_for_project(project_code=args.project)
                    for t in rows:
                        print(
                            f"{t.takeoff_id} | project={t.project_code} | "
                            f"template={t.template_code} | "
                            f"tax_rate={t.tax_rate} | created_at={t.created_at}"
                        )
                    return 0

                if args.takeoffs_cmd == "show":
                    t = takeoff_repo.get(takeoff_id=args.id)
                    print(
                        f"{t.takeoff_id} | project={t.project_code} | "
                        f"template={t.template_code} | "
                        f"tax_rate={t.tax_rate} | "
                        f"created_at={t.created_at}"
                    )
                    print("---- lines ----")
                    lines = takeoff_line_repo.list_for_takeoff(takeoff_id=args.id)
                    for ln in lines:
                        taxable = "taxable" if ln.taxable_snapshot else "non-taxable"
                        print(
                            f"{ln.item_code} | qty={ln.qty} | {taxable} | "
                            f"unit_price={ln.unit_price_snapshot} | {ln.description_snapshot}"
                        )
                    return 0

                if args.takeoffs_cmd == "render":
                    fmt = OutputFormat(args.format)
                    out = Path(args.out)
                    out.parent.mkdir(parents=True, exist_ok=True)

                    rendered_path = RenderTakeoffFromSnapshot(
                        project_repo=project_repo,
                        template_repo=template_repo,
                        takeoff_repo=takeoff_repo,
                        takeoff_line_repo=takeoff_line_repo,
                        renderer_factory=RendererRegistry(),
                        config=config,
                    )(takeoff_id=args.id, out=out, fmt=fmt)

                    print(f"{fmt.value.upper()} generated at: {rendered_path.resolve()}")
                    return 0

                raise AssertionError("Unreachable: unknown takeoffs command")

            finally:
                conn.close()

        raise AssertionError("Unreachable: unknown command")

    except InvalidInputError as e:
        print(str(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())