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
from app.application.render_takeoff_from_snapshot import (
    RenderTakeoffFromSnapshot,
    RenderTakeoffFromVersion,
)
from app.application.save_takeoff import SaveTakeoff
from app.application.seed_takeoff_from_template import SeedTakeoffFromTemplate
from app.config import AppConfig
from app.domain.output_format import OutputFormat
from app.domain.project import Project
from app.domain.stage import Stage
from app.domain.template import Template
from app.domain.template_line import TemplateLine
from app.domain.totals import TakeoffLineInput, calc_grand_totals, calc_stage_totals
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
        p_add.add_argument("--valve-discount", default="0.00")

        p_list = projects_sub.add_parser("list")
        p_list.add_argument("--all", action="store_true", help="Include inactive projects")

        p_show = projects_sub.add_parser("show")
        p_show.add_argument("--code", required=True)
        
        p_set = projects_sub.add_parser("set-valve-discount")
        p_set.add_argument("--code", required=True)
        p_set.add_argument("--amount", required=True)

        p_del = projects_sub.add_parser("delete")
        p_del.add_argument("--code", required=True)

        # -------------------------
        # templates (SQLite)
        # -------------------------
        templates = sub.add_parser("templates")
        templates_sub = templates.add_subparsers(dest="templates_cmd", required=True)

        t_add = templates_sub.add_parser("add")
        t_add.add_argument("--code", required=True)
        t_add.add_argument("--name", required=True)
        t_add.add_argument("--category", required=True)
        t_add.add_argument("--inactive", action="store_true")

        t_list = templates_sub.add_parser("list")
        t_list.add_argument("--all", action="store_true", help="Include inactive templates")

        t_show = templates_sub.add_parser("show")
        t_show.add_argument("--code", required=True)

        t_del = templates_sub.add_parser("delete")
        t_del.add_argument("--code", required=True)

        # -------------------------
        # template-lines (SQLite)
        # -------------------------
        tlines = sub.add_parser("template-lines")
        tlines_sub = tlines.add_subparsers(dest="tlines_cmd", required=True)

        tl_add = tlines_sub.add_parser("add")
        tl_add.add_argument("--template", required=True)
        tl_add.add_argument("--item", required=True)
        tl_add.add_argument("--qty", required=True)
        tl_add.add_argument("--stage", choices=["ground", "topout", "final"], default="final")
        tl_add.add_argument("--factor", default="1.0")
        tl_add.add_argument("--sort-order", default="0")
        tl_add.add_argument("--notes", default=None)

        tl_list = tlines_sub.add_parser("list")
        tl_list.add_argument("--template", required=True)

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

        lines_cmd = takeoffs_sub.add_parser("lines")
        lines_cmd.add_argument("--id", required=True)

        upd = takeoffs_sub.add_parser("update-line")
        upd.add_argument("--id", required=True)
        upd.add_argument("--item", required=True)
        upd.add_argument("--qty", required=False)
        upd.add_argument("--stage", choices=["ground", "topout", "final"], required=False)
        upd.add_argument("--factor", required=False)
        upd.add_argument("--sort-order", required=False)

        rnd = takeoffs_sub.add_parser("render")
        rnd.add_argument("--id", required=True)
        rnd.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
        rnd.add_argument("--out", required=True)
        
        snap = takeoffs_sub.add_parser("snapshot")
        snap.add_argument("--id", required=True)
        snap.add_argument("--notes", default=None)

        vers = takeoffs_sub.add_parser("versions")
        vers.add_argument("--id", required=True)

        # Alias: version (singular)
        ver_alias = takeoffs_sub.add_parser("version")
        ver_alias.add_argument("--id", required=True)

        rv = takeoffs_sub.add_parser("render-version")
        rv.add_argument("--version-id", required=True)
        rv.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
        rv.add_argument("--out", required=True)

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
                            valve_discount=_parse_decimal(args.valve_discount, "--valve-discount"),
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
                            f"foreman={p.foreman} | {active} | valve_discount={p.valve_discount}"
                        )
                    return 0

                if args.projects_cmd == "show":
                    p = project_repo.get(code=args.code)
                    active = "active" if p.is_active else "inactive"
                    print(
                        f"{p.code} | {p.name} | contractor={p.contractor} | "
                        f"foreman={p.foreman} | {active} | valve_discount={p.valve_discount}"
                    )
                    return 0
                
                if args.projects_cmd == "set-valve-discount":
                    amount = _parse_decimal(args.amount, "--amount")
                    project_repo.set_valve_discount(code=args.code, valve_discount=amount)
                    print(f"PROJECT policy updated code={args.code} valve_discount={amount}")
                    return 0

                if args.projects_cmd == "delete":
                    project_repo.delete(code=args.code)
                    print(f"PROJECT deleted code={args.code}")
                    return 0

                raise AssertionError("Unreachable: unknown projects command")

            finally:
                conn.close()

        # -------------------------
        # TEMPLATES (SQLite)
        # -------------------------
        if args.cmd == "templates":
            conn = SqliteDb(path=Path(args.db_path)).connect()
            try:
                template_repo = SqliteTemplateRepository(conn=conn)

                if args.templates_cmd == "add":
                    template_repo.upsert(
                        Template(
                            code=args.code,
                            name=args.name,
                            category=args.category,
                            is_active=not args.inactive,
                        )
                    )
                    status = "inactive" if args.inactive else "active"
                    print(f"TEMPLATE saved code={args.code} status={status}")
                    return 0

                if args.templates_cmd == "list":
                    rows = template_repo.list(include_inactive=bool(args.all))
                    for t in rows:
                        active = "active" if t.is_active else "inactive"
                        print(f"{t.code} | {t.name} | category={t.category} | {active}")
                    return 0

                if args.templates_cmd == "show":
                    t = template_repo.get(code=args.code)
                    active = "active" if t.is_active else "inactive"
                    print(f"{t.code} | {t.name} | category={t.category} | {active}")
                    return 0

                if args.templates_cmd == "delete":
                    template_repo.delete(code=args.code)
                    print(f"TEMPLATE deleted code={args.code}")
                    return 0

                raise AssertionError("Unreachable: unknown templates command")

            finally:
                conn.close()

        # -------------------------
        # TEMPLATE LINES (SQLite)
        # -------------------------
        if args.cmd == "template-lines":
            conn = SqliteDb(path=Path(args.db_path)).connect()
            try:
                line_repo = SqliteTemplateLineRepository(conn=conn)

                if args.tlines_cmd == "add":
                    line_repo.upsert(
                        TemplateLine(
                            template_code=args.template,
                            item_code=args.item,
                            qty=Decimal(args.qty),
                            stage=Stage(args.stage),
                            factor=Decimal(args.factor),
                            sort_order=int(args.sort_order),
                            notes=args.notes,
                        )
                    )
                    print(
                        f"TEMPLATE LINE saved template={args.template} "
                        f"item={args.item} qty={args.qty}"
                    )
                    return 0

                if args.tlines_cmd == "list":
                    rows = line_repo.list_for_template(template_code=args.template)
                    for ln in rows:
                        notes = ln.notes or ""
                        print(
                            f"{ln.template_code} | {ln.item_code} | qty={ln.qty} | "
                            f"stage={ln.stage.value} | factor={ln.factor} | sort_order={ln.sort_order} | {notes}"
                        )
                    return 0

                raise AssertionError("Unreachable: unknown template-lines command")

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

                    try:
                        takeoff_id = use_case(
                            project_code=args.project,
                            template_code=args.template,
                            tax_rate_override=tax_rate,
                        )
                    except InvalidInputError as e:
                        msg = str(e)
                        if msg.startswith("Takeoff already exists for project=") and " id=" in msg:
                            existing_id = msg.rsplit(" id=", 1)[1].strip()
                            print(msg)
                            print()
                            print("NEXT:")
                            print(
                                f"  python -m app.cli --db-path {args.db_path} "
                                f"takeoffs show --id {existing_id}"
                            )
                            print(
                                f"  python -m app.cli --db-path {args.db_path} "
                                f"takeoffs snapshot --id {existing_id}"
                            )
                            print(
                                f"  python -m app.cli --db-path {args.db_path} "
                                f"takeoffs render --id {existing_id} --format pdf --out output/takeoff.pdf"
                            )
                            return 2
                        raise

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
                            f"tax_rate={t.tax_rate} | created_at={t.created_at} | valve_discount={t.valve_discount}"
                        )
                    return 0

                if args.takeoffs_cmd == "show":
                    t = takeoff_repo.get(takeoff_id=args.id)
                    print(
                        f"TAKEOFF {t.takeoff_id} | project={t.project_code} | "
                        f"template={t.template_code} | tax_rate={t.tax_rate} | "
                        f"created_at={t.created_at} | valve_discount={t.valve_discount}"
                    )

                    print("---- lines ----")
                    lines = list(takeoff_line_repo.list_for_takeoff(takeoff_id=args.id))

                    for ln in lines:
                        taxable = "taxable" if ln.taxable_snapshot else "non-taxable"
                        stage = getattr(ln, "stage", None)
                        stage_txt = stage.value if stage is not None else ""
                        factor_txt = getattr(ln, "factor", "")
                        sort_txt = getattr(ln, "sort_order", "")
                        print(
                            f"{ln.item_code} | qty={ln.qty} | stage={stage_txt} | "
                            f"factor={factor_txt} | sort_order={sort_txt} | {taxable} | "
                            f"unit_price={ln.unit_price_snapshot} | {ln.description_snapshot}"
                        )

                    # ---- totals (debug) ----
                    print("---- totals ----")

                    inputs: list[TakeoffLineInput] = []
                    for ln in lines:
                        st = getattr(ln, "stage", None) or Stage.FINAL
                        factor = getattr(ln, "factor", None) or Decimal("1.0")
                        inputs.append(
                            TakeoffLineInput(
                                stage=st,
                                price=ln.unit_price_snapshot,
                                qty=ln.qty,
                                factor=factor,
                                taxable=ln.taxable_snapshot,
                            )
                        )

                    for st in (Stage.GROUND, Stage.TOPOUT, Stage.FINAL):
                        tt = calc_stage_totals(inputs, stage=st, tax_rate=t.tax_rate)
                        print(
                            f"{st.value.upper():<6} | subtotal={tt.subtotal:.2f} | "
                            f"tax={tt.tax:.2f} | total={tt.total:.2f}"
                        )

                    valve_discount = t.valve_discount
                    gt = calc_grand_totals(
                        inputs,
                        valve_discount=valve_discount,
                        tax_rate=t.tax_rate,
                    )
                    print(
                        f"GRAND  | subtotal={gt.subtotal:.2f} | tax={gt.tax:.2f} | "
                        f"total={gt.total:.2f} | valve_discount={gt.valve_discount:.2f} | "
                        f"after_discount={gt.total_after_discount:.2f}"
                    )
                    return 0

                if args.takeoffs_cmd == "lines":
                    lines = list(takeoff_line_repo.list_for_takeoff(takeoff_id=args.id))
                    if not lines:
                        print(f"No lines found for takeoff_id={args.id}")
                        return 0

                    for ln in lines:
                        taxable = "taxable" if ln.taxable_snapshot else "non-taxable"
                        stage = getattr(ln, "stage", None)
                        stage_txt = stage.value if stage is not None else ""
                        factor_txt = getattr(ln, "factor", "")
                        sort_txt = getattr(ln, "sort_order", "")
                        print(
                            f"{ln.item_code} | qty={ln.qty} | stage={stage_txt} | "
                            f"factor={factor_txt} | sort_order={sort_txt} | {taxable} | "
                            f"unit_price={ln.unit_price_snapshot} | {ln.description_snapshot}"
                        )
                    return 0

                if args.takeoffs_cmd == "update-line":
                    qty: Decimal | None = None
                    factor: Decimal | None = None
                    stage: Stage | None = None
                    sort_order: int | None = None

                    if args.qty is not None:
                        qty = _parse_decimal(args.qty, "--qty")
                    if args.factor is not None:
                        factor = _parse_decimal(args.factor, "--factor")
                    if args.stage is not None:
                        stage = Stage(args.stage)
                    if args.sort_order is not None:
                        try:
                            sort_order = int(args.sort_order)
                        except Exception as e:
                            raise SystemExit(f"Invalid --sort-order: {args.sort_order!r}") from e

                    if qty is None and factor is None and stage is None and sort_order is None:
                        raise SystemExit(
                            "At least one of --qty, --stage, --factor, --sort-order must be provided"
                        )

                    takeoff_line_repo.update_line(
                        takeoff_id=args.id,
                        item_code=args.item,
                        qty=qty,
                        stage=stage,
                        factor=factor,
                        sort_order=sort_order,
                    )
                    print(
                        f"TAKEOFF line updated takeoff_id={args.id} item={args.item}"
                    )
                    print()
                    print("NEXT:")
                    print(
                        f"  python -m app.cli --db-path {args.db_path} takeoffs lines --id {args.id}"
                    )
                    print(
                        f"  python -m app.cli --db-path {args.db_path} takeoffs show --id {args.id}"
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
                
                if args.takeoffs_cmd == "snapshot":
                    version_id = takeoff_repo.create_snapshot_version(
                        takeoff_id=args.id,
                        notes=args.notes,
                    )
                    v = takeoff_repo.get_version(version_id=version_id)
                    print(
                        f"TAKEOFF snapshot created version_id={v.version_id} "
                        f"takeoff_id={v.takeoff_id} v{v.version_number} created_at={v.created_at}"
                    )

                    # UX: print next-step commands (copy/paste friendly)
                    print()
                    print("NEXT:")
                    print(f"  python -m app.cli --db-path {args.db_path} takeoffs versions --id {v.takeoff_id}")
                    print(
                        "  python -m app.cli --db-path "
                        f"{args.db_path} takeoffs render-version --version-id {v.version_id} "
                        "--format pdf --out output/version.pdf"
                    )
                    return 0

                if args.takeoffs_cmd in ("versions", "version"):
                    rows = takeoff_repo.list_versions(takeoff_id=args.id)
                    if not rows:
                        print(f"No versions found for takeoff_id={args.id}")
                        return 0
                    for v in rows:
                        notes = v.notes or ""
                        print(
                            f"{v.version_id} | takeoff_id={v.takeoff_id} | "
                            f"v{v.version_number} | tax_rate={v.tax_rate_snapshot} | "
                            f"valve_discount={v.valve_discount_snapshot} | {v.created_at} | {notes}"
                        )
                    return 0

                if args.takeoffs_cmd == "render-version":
                    fmt = OutputFormat(args.format)
                    out = Path(args.out)
                    out.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        rendered_path = RenderTakeoffFromVersion(
                            project_repo=project_repo,
                            template_repo=template_repo,
                            takeoff_repo=takeoff_repo,
                            renderer_factory=RendererRegistry(),
                            config=config,
                        )(version_id=args.version_id, out=out, fmt=fmt)
                    except InvalidInputError as e:
                        # Common UX mistake: user passes takeoff_id instead of version_id
                        try:
                            _ = takeoff_repo.get(takeoff_id=args.version_id)
                        except InvalidInputError:
                            raise  # original error: truly unknown id
                        else:
                            print(str(e))
                            print()
                            print("It looks like you passed a TAKEOFF id, but this command needs a VERSION id.")
                            print("Run this to list versions for that takeoff:")
                            print(
                                f"  python -m app.cli --db-path {args.db_path} takeoffs versions --id {args.version_id}"
                            )
                            return 2

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