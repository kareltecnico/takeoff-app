from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path
import json
import re
from uuid import uuid4

from app.application.build_sample_takeoff import BuildSampleTakeoff
from app.application.errors import InvalidInputError
from app.application.generate_revision_report import GenerateRevisionReport
from app.application.export_revision_bundle import ExportRevisionBundle
from app.application.import_items_from_csv import ImportItemsFromCsv
from app.application.input_sources import TakeoffInputSource
from app.application.inputs.factory_takeoff_input import FactoryTakeoffInput
from app.application.inputs.json_takeoff_input import JsonTakeoffInput
from app.application.inputs.repo_takeoff_input import RepoTakeoffInput
from app.application.items_catalog import ItemsCatalog
from app.application.render_takeoff import RenderTakeoff
from app.application.render_takeoff_from_snapshot import (
    RenderTakeoffFromSnapshot,
    RenderTakeoffFromVersion,
)
from app.application.save_takeoff import SaveTakeoff
from app.application.diff_takeoff_versions import DiffTakeoffVersions
from app.application.seed_takeoff_from_template import SeedTakeoffFromTemplate
from app.application.add_takeoff_line import AddTakeoffLine
from app.application.delete_takeoff_line import DeleteTakeoffLine
from app.application.list_takeoff_lines import ListTakeoffLines
from app.application.update_takeoff_line import UpdateTakeoffLine
from app.application.inspect_takeoff import InspectTakeoff
from app.application.summarize_project import SummarizeProject
from app.application.generate_project_invoice import GenerateProjectInvoice
from app.application.generate_takeoff_from_plan_reading import (
    GenerateTakeoffFromPlanReading,
)
from app.config import AppConfig
from app.domain.output_format import OutputFormat
from app.domain.fixture_mapping import (
    FixtureQuantityRef,
    FixtureQuantitySourceKind,
    ProjectFixtureOverride,
    TemplateFixtureMappingRule,
)
from app.domain.plan_reading_input import PlanReadingInput
from app.domain.project import Project
from app.domain.stage import Stage
from app.domain.takeoff_line_snapshot import TakeoffLineSnapshot
from app.domain.template import Template
from app.domain.template_line import TemplateLine
from app.domain.totals import TakeoffLineInput, calc_grand_totals, calc_stage_totals
from app.infrastructure.file_takeoff_repository import FileTakeoffRepository
from app.infrastructure.renderer_registry import RendererRegistry
from app.infrastructure.sqlite_db import SqliteDb
from app.infrastructure.sqlite_item_repository import SqliteItemRepository
from app.infrastructure.sqlite_project_fixture_override_repository import (
    SqliteProjectFixtureOverrideRepository,
)
from app.infrastructure.sqlite_project_repository import SqliteProjectRepository
from app.infrastructure.sqlite_takeoff_line_repository import SqliteTakeoffLineRepository
from app.infrastructure.sqlite_takeoff_repository import SqliteTakeoffRepository
from app.infrastructure.sqlite_template_fixture_mapping_repository import (
    SqliteTemplateFixtureMappingRepository,
)
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


def _parse_non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except Exception as e:
        raise argparse.ArgumentTypeError(f"expected integer, got {value!r}") from e
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def _parse_non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except Exception as e:
        raise argparse.ArgumentTypeError(f"expected number, got {value!r}") from e
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def _parse_bool_flag(value: str, flag: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "t", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "f", "0", "no", "n", "off"}:
        return False
    raise SystemExit(f"Invalid {flag}: {value!r} (use true/false)")


def _validate_item_code(code: str, flag: str = "--code") -> str:
    normalized = code.strip()
    if not normalized:
        raise InvalidInputError(f"{flag} cannot be empty")
    if not re.fullmatch(r"[A-Z0-9_]+", normalized):
        raise InvalidInputError(
            f"{flag} must contain only A-Z, 0-9, and _"
        )
    return normalized


def _validate_non_empty_text(value: str | None, flag: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise InvalidInputError(f"{flag} cannot be empty")
    return normalized


def _parse_source_kind(value: str) -> FixtureQuantitySourceKind:
    try:
        return FixtureQuantitySourceKind(value)
    except ValueError as e:
        raise InvalidInputError(f"Invalid --source-kind: {value!r}") from e


def _effective_notes(
    *,
    current: str | None,
    value: str | None,
    clear: bool,
) -> str | None:
    if clear:
        return None
    if value is not None:
        return value
    return current


def _add_plan_reading_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--stories", required=True, type=_parse_non_negative_int)
    parser.add_argument("--kitchens", required=True, type=_parse_non_negative_int)
    parser.add_argument("--garbage-disposals", required=True, type=_parse_non_negative_int)
    parser.add_argument("--laundry-rooms", required=True, type=_parse_non_negative_int)
    parser.add_argument("--lav-faucets", required=True, type=_parse_non_negative_int)
    parser.add_argument("--toilets", required=True, type=_parse_non_negative_int)
    parser.add_argument("--showers", required=True, type=_parse_non_negative_int)
    parser.add_argument("--bathtubs", required=True, type=_parse_non_negative_int)
    parser.add_argument("--half-baths", required=True, type=_parse_non_negative_int)
    parser.add_argument("--double-bowl-vanities", required=True, type=_parse_non_negative_int)
    parser.add_argument("--hose-bibbs", required=True, type=_parse_non_negative_int)
    parser.add_argument("--ice-makers", required=True, type=_parse_non_negative_int)
    parser.add_argument("--water-heater-tank-qty", required=True, type=_parse_non_negative_int)
    parser.add_argument(
        "--water-heater-tankless-qty",
        required=True,
        type=_parse_non_negative_int,
    )
    parser.add_argument("--sewer-distance-lf", required=True, type=_parse_non_negative_float)
    parser.add_argument("--water-distance-lf", required=True, type=_parse_non_negative_float)


def _build_fixture_quantity_ref(
    *,
    source_kind: FixtureQuantitySourceKind,
    source_name: str | None,
    constant_qty: Decimal | None,
) -> FixtureQuantityRef:
    final_source_name = source_name.strip() if source_name is not None else None
    if final_source_name == "":
        raise InvalidInputError("--source-name cannot be empty")

    if source_kind == FixtureQuantitySourceKind.CONSTANT:
        if constant_qty is None:
            raise InvalidInputError("Final source_kind=constant requires --constant-qty")
        return FixtureQuantityRef(
            source_kind=source_kind,
            source_name=None,
            constant_qty=constant_qty,
        )

    if final_source_name is None:
        raise InvalidInputError(
            f"Final source_kind={source_kind.value} requires --source-name"
        )
    return FixtureQuantityRef(
        source_kind=source_kind,
        source_name=final_source_name,
        constant_qty=None,
    )


def _validate_out_extension(fmt: OutputFormat, out: Path) -> None:
    expected = f".{fmt.value}"
    if out.suffix.lower() != expected:
        raise SystemExit(f"--out must end with {expected} for --format {fmt.value}")


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _project_models_label(template_codes: list[str]) -> str:
    if not template_codes:
        return "NO_MODELS"
    return ",".join(template_codes)


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




def _handle_items(args: argparse.Namespace, *, db_path: Path) -> int:
    conn = SqliteDb(path=db_path).connect()
    try:
        repo = SqliteItemRepository(conn=conn)
        catalog = ItemsCatalog(repo=repo)

        if args.items_cmd == "import":
            report = ImportItemsFromCsv(repo=repo)(csv_path=Path(args.csv))
            print("ITEM IMPORT")
            print(f"inserted={report.inserted}")
            print(f"updated={report.updated}")
            print(f"skipped={report.skipped}")
            print(f"conflicted={report.conflicted}")
            for issue in report.skipped_rows:
                code_txt = issue.code or "-"
                print(f"SKIPPED row={issue.row_number} code={code_txt} reason={issue.reason}")
            for issue in report.conflicted_rows:
                code_txt = issue.code or "-"
                print(f"CONFLICT row={issue.row_number} code={code_txt} reason={issue.reason}")
            return 0

        if args.items_cmd == "add":
            code = _validate_item_code(args.code)
            description = _validate_non_empty_text(args.description, "--description")
            item_number = _validate_non_empty_text(args.item_number, "--item-number")
            details = _validate_non_empty_text(args.details, "--details")
            catalog.add(
                code=code,
                description=description or "",
                unit_price=_parse_decimal(args.unit_price, "--unit-price"),
                taxable=_parse_bool_flag(args.taxable, "--taxable"),
                item_number=item_number,
                details=details,
                is_active=not args.inactive,
            )
            print(f"ITEM saved code={code}")
            return 0

        if args.items_cmd == "list":
            rows = catalog.list(include_inactive=bool(args.include_inactive))
            for item in rows:
                active = "active" if item.is_active else "inactive"
                print(
                    f"{item.code} | item_number={item.item_number} | "
                    f"description={item.description} | details={item.details} | "
                    f"unit_price={item.unit_price} | taxable={item.taxable} | {active}"
                )
            return 0

        if args.items_cmd == "get":
            item = catalog.get(code=_validate_item_code(args.code))
            active = "active" if item.is_active else "inactive"
            print(
                f"{item.code} | item_number={item.item_number} | "
                f"description={item.description} | details={item.details} | "
                f"unit_price={item.unit_price} | taxable={item.taxable} | {active}"
            )
            return 0

        if args.items_cmd == "update":
            code = _validate_item_code(args.code)
            description = _validate_non_empty_text(args.description, "--description")
            item_number = _validate_non_empty_text(args.item_number, "--item-number")
            details = _validate_non_empty_text(args.details, "--details")
            taxable = (
                _parse_bool_flag(args.taxable, "--taxable")
                if args.taxable is not None
                else None
            )
            unit_price = (
                _parse_decimal(args.unit_price, "--unit-price")
                if args.unit_price is not None
                else None
            )
            catalog.update(
                code=code,
                description=description,
                unit_price=unit_price,
                taxable=taxable,
                item_number=item_number,
                details=details,
                clear_item_number=bool(args.clear_item_number),
                clear_details=bool(args.clear_details),
            )
            print(f"ITEM updated code={code}")
            return 0

        if args.items_cmd == "activate":
            code = _validate_item_code(args.code)
            catalog.update(code=code, is_active=True)
            print(f"ITEM activated code={code}")
            return 0

        if args.items_cmd == "deactivate":
            code = _validate_item_code(args.code)
            catalog.update(code=code, is_active=False)
            print(f"ITEM deactivated code={code}")
            return 0

        raise AssertionError("Unreachable: unknown items command")
    finally:
        conn.close()


def _handle_fixture_mappings(args: argparse.Namespace, *, db_path: Path) -> int:
    conn = SqliteDb(path=db_path).connect()
    try:
        repo = SqliteTemplateFixtureMappingRepository(conn=conn)

        if args.fm_cmd == "add":
            mapping_id = (
                _validate_non_empty_text(args.mapping_id, "--mapping-id")
                if args.mapping_id is not None
                else uuid4().hex
            )
            source_kind = _parse_source_kind(args.source_kind)
            quantity_ref = _build_fixture_quantity_ref(
                source_kind=source_kind,
                source_name=args.source_name,
                constant_qty=(
                    _parse_decimal(args.constant_qty, "--constant-qty")
                    if args.constant_qty is not None
                    else None
                ),
            )
            repo.add(
                TemplateFixtureMappingRule(
                    mapping_id=mapping_id or "",
                    template_code=_validate_non_empty_text(args.template, "--template") or "",
                    quantity_ref=quantity_ref,
                    item_code=_validate_item_code(args.item, "--item"),
                    qty_multiplier=_parse_decimal(args.qty_multiplier, "--qty-multiplier"),
                    stage=Stage(args.stage),
                    factor=_parse_decimal(args.factor, "--factor"),
                    sort_order=int(args.sort_order),
                    notes=_validate_non_empty_text(args.notes, "--notes"),
                    is_active=not args.inactive,
                )
            )
            print(f"FIXTURE MAPPING saved mapping_id={mapping_id}")
            return 0

        if args.fm_cmd == "list":
            rows = repo.list_for_template(
                _validate_non_empty_text(args.template, "--template") or "",
                include_inactive=bool(args.include_inactive),
            )
            for rule in rows:
                ref = rule.quantity_ref
                print(
                    f"{rule.mapping_id} | template={rule.template_code} | "
                    f"source_kind={ref.source_kind.value} | source_name={ref.source_name} | "
                    f"constant_qty={ref.constant_qty} | item={rule.item_code} | "
                    f"qty_multiplier={rule.qty_multiplier} | stage={rule.stage.value} | "
                    f"factor={rule.factor} | sort_order={rule.sort_order} | "
                    f"notes={rule.notes} | active={rule.is_active}"
                )
            return 0

        if args.fm_cmd == "show":
            rule = repo.get(_validate_non_empty_text(args.mapping_id, "--mapping-id") or "")
            ref = rule.quantity_ref
            print(
                f"{rule.mapping_id} | template={rule.template_code} | "
                f"source_kind={ref.source_kind.value} | source_name={ref.source_name} | "
                f"constant_qty={ref.constant_qty} | item={rule.item_code} | "
                f"qty_multiplier={rule.qty_multiplier} | stage={rule.stage.value} | "
                f"factor={rule.factor} | sort_order={rule.sort_order} | "
                f"notes={rule.notes} | active={rule.is_active}"
            )
            return 0

        if args.fm_cmd == "update":
            current = repo.get(_validate_non_empty_text(args.mapping_id, "--mapping-id") or "")
            final_source_kind = (
                _parse_source_kind(args.source_kind)
                if args.source_kind is not None
                else current.quantity_ref.source_kind
            )
            source_name_value = (
                _validate_non_empty_text(args.source_name, "--source-name")
                if args.source_name is not None
                else current.quantity_ref.source_name
            )
            constant_qty_value = (
                _parse_decimal(args.constant_qty, "--constant-qty")
                if args.constant_qty is not None
                else current.quantity_ref.constant_qty
            )
            quantity_ref = _build_fixture_quantity_ref(
                source_kind=final_source_kind,
                source_name=source_name_value,
                constant_qty=constant_qty_value,
            )
            repo.upsert(
                TemplateFixtureMappingRule(
                    mapping_id=current.mapping_id,
                    template_code=current.template_code,
                    quantity_ref=quantity_ref,
                    item_code=(
                        _validate_item_code(args.item, "--item")
                        if args.item is not None
                        else current.item_code
                    ),
                    qty_multiplier=(
                        _parse_decimal(args.qty_multiplier, "--qty-multiplier")
                        if args.qty_multiplier is not None
                        else current.qty_multiplier
                    ),
                    stage=Stage(args.stage) if args.stage is not None else current.stage,
                    factor=(
                        _parse_decimal(args.factor, "--factor")
                        if args.factor is not None
                        else current.factor
                    ),
                    sort_order=int(args.sort_order) if args.sort_order is not None else current.sort_order,
                    notes=_effective_notes(
                        current=current.notes,
                        value=_validate_non_empty_text(args.notes, "--notes"),
                        clear=bool(args.clear_notes),
                    ),
                    is_active=current.is_active,
                )
            )
            print(f"FIXTURE MAPPING updated mapping_id={current.mapping_id}")
            return 0

        if args.fm_cmd == "activate":
            mapping_id = _validate_non_empty_text(args.mapping_id, "--mapping-id") or ""
            repo.set_active(mapping_id, is_active=True)
            print(f"FIXTURE MAPPING activated mapping_id={mapping_id}")
            return 0

        if args.fm_cmd == "deactivate":
            mapping_id = _validate_non_empty_text(args.mapping_id, "--mapping-id") or ""
            repo.set_active(mapping_id, is_active=False)
            print(f"FIXTURE MAPPING deactivated mapping_id={mapping_id}")
            return 0

        raise AssertionError("Unreachable: unknown fixture-mappings command")
    finally:
        conn.close()


def _handle_project_overrides(args: argparse.Namespace, *, db_path: Path) -> int:
    conn = SqliteDb(path=db_path).connect()
    try:
        repo = SqliteProjectFixtureOverrideRepository(conn=conn)

        if args.po_cmd == "set":
            project_code = _validate_non_empty_text(args.project, "--project") or ""
            mapping_id = _validate_non_empty_text(args.mapping_id, "--mapping-id") or ""
            try:
                current = repo.get(project_code=project_code, mapping_id=mapping_id)
            except InvalidInputError:
                current = ProjectFixtureOverride(project_code=project_code, mapping_id=mapping_id)

            if args.clear_item and args.item is not None:
                raise InvalidInputError("Use either --item or --clear-item, not both")
            if args.clear_notes and args.notes is not None:
                raise InvalidInputError("Use either --notes or --clear-notes, not both")
            if args.disable and args.item is not None:
                raise InvalidInputError("--disable cannot be combined with --item")

            final_item = (
                None
                if args.clear_item
                else _validate_item_code(args.item, "--item")
                if args.item is not None
                else current.item_code_override
            )
            final_notes = _effective_notes(
                current=current.notes_override,
                value=_validate_non_empty_text(args.notes, "--notes"),
                clear=bool(args.clear_notes),
            )
            final_disabled = True if args.disable else current.is_disabled

            if not final_disabled and final_item is None and final_notes is None:
                raise InvalidInputError(
                    "Final project override state is empty; use delete instead"
                )

            repo.upsert(
                ProjectFixtureOverride(
                    project_code=project_code,
                    mapping_id=mapping_id,
                    is_disabled=final_disabled,
                    item_code_override=final_item,
                    notes_override=final_notes,
                )
            )
            print(f"PROJECT OVERRIDE saved project={project_code} mapping_id={mapping_id}")
            return 0

        if args.po_cmd == "list":
            project_code = _validate_non_empty_text(args.project, "--project") or ""
            rows = repo.list_for_project(project_code)
            for row in rows:
                print(
                    f"{row.project_code} | mapping_id={row.mapping_id} | "
                    f"disabled={row.is_disabled} | item={row.item_code_override} | "
                    f"notes={row.notes_override}"
                )
            return 0

        if args.po_cmd == "show":
            row = repo.get(
                project_code=_validate_non_empty_text(args.project, "--project") or "",
                mapping_id=_validate_non_empty_text(args.mapping_id, "--mapping-id") or "",
            )
            print(
                f"{row.project_code} | mapping_id={row.mapping_id} | "
                f"disabled={row.is_disabled} | item={row.item_code_override} | "
                f"notes={row.notes_override}"
            )
            return 0

        if args.po_cmd == "delete":
            project_code = _validate_non_empty_text(args.project, "--project") or ""
            mapping_id = _validate_non_empty_text(args.mapping_id, "--mapping-id") or ""
            repo.delete(project_code=project_code, mapping_id=mapping_id)
            print(f"PROJECT OVERRIDE deleted project={project_code} mapping_id={mapping_id}")
            return 0

        raise AssertionError("Unreachable: unknown project-overrides command")
    finally:
        conn.close()


def _handle_projects(args: argparse.Namespace, *, db_path: Path) -> int:
    conn = SqliteDb(path=db_path).connect()
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

        if args.projects_cmd == "summary":
            _ = project_repo.get(code=args.code)  # validate project exists
            takeoff_repo = SqliteTakeoffRepository(conn=conn)
            takeoff_line_repo = SqliteTakeoffLineRepository(conn=conn)

            result = SummarizeProject(
                takeoff_repo=takeoff_repo,
                takeoff_line_repo=takeoff_line_repo,
            )(project_code=args.code)

            print("PROJECT SUMMARY")
            print(f"code={result.project_code}")
            print(f"takeoffs={result.takeoff_count}")
            print()

            print("TAKEOFFS")
            if not result.takeoffs:
                print("none")
            else:
                for t in result.takeoffs:
                    print(
                        f"{t.template_code} | takeoff_id={t.takeoff_id} | "
                        f"subtotal={t.subtotal:.2f} | tax={t.tax:.2f} | "
                        f"total={t.total:.2f} | valve_discount={t.valve_discount:.2f} | "
                        f"after_discount={t.total_after_discount:.2f}"
                    )
            print()

            print("GRAND TOTAL")
            print(f"subtotal={result.subtotal:.2f}")
            print(f"tax={result.tax:.2f}")
            print(f"total={result.total:.2f}")
            print(f"valve_discount={result.valve_discount:.2f}")
            print(f"after_discount={result.total_after_discount:.2f}")
            return 0

        if args.projects_cmd == "invoice":
            _ = project_repo.get(code=args.code)  # ensure project exists

            takeoff_repo = SqliteTakeoffRepository(conn=conn)
            takeoff_line_repo = SqliteTakeoffLineRepository(conn=conn)

            result = GenerateProjectInvoice(
                takeoff_repo=takeoff_repo,
                takeoff_line_repo=takeoff_line_repo,
            )(project_code=args.code)

            print("PROJECT INVOICE")
            print(f"code={result.project_code}")
            print(f"takeoffs={result.takeoff_count}")
            print()

            print("STAGE TOTALS")
            print(
                f"GROUND | subtotal={result.ground_subtotal:.2f} | tax={result.ground_tax:.2f} | total={result.ground_total:.2f}"
            )
            print(
                f"TOPOUT | subtotal={result.topout_subtotal:.2f} | tax={result.topout_tax:.2f} | total={result.topout_total:.2f}"
            )
            print(
                f"FINAL  | subtotal={result.final_subtotal:.2f} | tax={result.final_tax:.2f} | total={result.final_total:.2f}"
            )
            print()

            print("GRAND TOTAL")
            print(f"subtotal={result.subtotal:.2f}")
            print(f"tax={result.tax:.2f}")
            print(f"total={result.total:.2f}")
            print(f"valve_discount={result.valve_discount:.2f}")
            print(f"after_discount={result.total_after_discount:.2f}")
            print()

            print("MODELS")
            for t in result.takeoffs:
                print(
                    f"{t.template_code} | subtotal={t.subtotal:.2f} | tax={t.tax:.2f} | total={t.total:.2f} | after_discount={t.total_after_discount:.2f}"
                )

            return 0

        if args.projects_cmd == "export":
            project = project_repo.get(code=args.code)
            takeoff_repo = SqliteTakeoffRepository(conn=conn)
            takeoff_line_repo = SqliteTakeoffLineRepository(conn=conn)
            template_repo = SqliteTemplateRepository(conn=conn)

            result = SummarizeProject(
                takeoff_repo=takeoff_repo,
                takeoff_line_repo=takeoff_line_repo,
            )(project_code=args.code)

            out_root = Path(args.out_dir)
            out_root.mkdir(parents=True, exist_ok=True)
            project_dir = out_root / project.code
            project_dir.mkdir(parents=True, exist_ok=True)

            model_codes = [t.template_code for t in result.takeoffs]
            project_base_name = _safe_filename(
                f"{project.name} ({_project_models_label(model_codes)})"
            )

            summary_json_path = project_dir / f"{project_base_name}_project_summary.json"
            summary_txt_path = project_dir / f"{project_base_name}_project_summary.txt"
            financial_txt_path = project_dir / f"{project_base_name}_financial_summary.txt"

            summary_payload = {
                "project_code": result.project_code,
                "project_name": project.name,
                "takeoff_count": result.takeoff_count,
                "subtotal": str(result.subtotal),
                "tax": str(result.tax),
                "total": str(result.total),
                "valve_discount": str(result.valve_discount),
                "total_after_discount": str(result.total_after_discount),
                "takeoffs": [
                    {
                        "takeoff_id": t.takeoff_id,
                        "project_code": t.project_code,
                        "template_code": t.template_code,
                        "subtotal": str(t.subtotal),
                        "tax": str(t.tax),
                        "total": str(t.total),
                        "valve_discount": str(t.valve_discount),
                        "total_after_discount": str(t.total_after_discount),
                    }
                    for t in result.takeoffs
                ],
            }
            summary_json_path.write_text(
                json.dumps(summary_payload, indent=2),
                encoding="utf-8",
            )

            summary_lines = [
                "PROJECT SUMMARY",
                f"code={result.project_code}",
                f"name={project.name}",
                f"takeoffs={result.takeoff_count}",
                "",
                "TAKEOFFS",
            ]
            if not result.takeoffs:
                summary_lines.append("none")
            else:
                for t in result.takeoffs:
                    summary_lines.append(
                        f"{t.template_code} | takeoff_id={t.takeoff_id} | "
                        f"subtotal={t.subtotal:.2f} | tax={t.tax:.2f} | "
                        f"total={t.total:.2f} | valve_discount={t.valve_discount:.2f} | "
                        f"after_discount={t.total_after_discount:.2f}"
                    )
            summary_lines.extend(
                [
                    "",
                    "GRAND TOTAL",
                    f"subtotal={result.subtotal:.2f}",
                    f"tax={result.tax:.2f}",
                    f"total={result.total:.2f}",
                    f"valve_discount={result.valve_discount:.2f}",
                    f"after_discount={result.total_after_discount:.2f}",
                ]
            )
            summary_text = "\n".join(summary_lines)
            summary_txt_path.write_text(summary_text, encoding="utf-8")
            financial_txt_path.write_text(summary_text, encoding="utf-8")

            deliverable_dir = project_dir / "deliverable"
            deliverable_dir.mkdir(parents=True, exist_ok=True)

            exported = 0
            rendered_files = 0
            for t in result.takeoffs:
                versions = takeoff_repo.list_versions(takeoff_id=t.takeoff_id)
                if not versions:
                    continue

                latest = versions[0]
                template = template_repo.get(code=t.template_code)

                latest_dir = project_dir / "takeoffs" / t.template_code / "latest"
                latest_dir.mkdir(parents=True, exist_ok=True)

                bundle_dir = ExportRevisionBundle(
                    takeoff_repo=takeoff_repo,
                    project_repo=project_repo,
                    template_repo=template_repo,
                    config=AppConfig(),
                )(
                    version_id=latest.version_id,
                    out_dir=latest_dir,
                )
                print(
                    f"EXPORTED latest snapshot template={t.template_code} "
                    f"version_id={latest.version_id} -> {bundle_dir.resolve()}"
                )
                exported += 1

                deliverable_base = _safe_filename(f"{project.name} ({template.code})")
                for fmt in (OutputFormat.PDF, OutputFormat.CSV, OutputFormat.JSON):
                    out_path = deliverable_dir / f"{deliverable_base}.{fmt.value}"
                    RenderTakeoffFromVersion(
                        project_repo=project_repo,
                        template_repo=template_repo,
                        takeoff_repo=takeoff_repo,
                        renderer_factory=RendererRegistry(),
                        config=AppConfig(),
                    )(
                        version_id=latest.version_id,
                        out=out_path,
                        fmt=fmt,
                    )
                    rendered_files += 1

            print()
            print(f"PROJECT export completed at: {project_dir.resolve()}")
            print(f"summary_json={summary_json_path.resolve()}")
            print(f"summary_txt={summary_txt_path.resolve()}")
            print(f"financial_summary_txt={financial_txt_path.resolve()}")
            print(f"deliverable_dir={deliverable_dir.resolve()}")
            print(f"latest_snapshot_bundles={exported}")
            print(f"rendered_deliverable_files={rendered_files}")
            return 0

        if args.projects_cmd == "package":
            project = project_repo.get(code=args.code)

            out_root = Path(args.out_dir)
            project_dir = out_root / project.code

            if not project_dir.exists():
                raise SystemExit(
                    "Project has not been exported yet. Run:\n"
                    f"  python -m app.cli projects export --code {project.code}"
                )

            package_dir = out_root / f"{project.code}_PACKAGE"
            package_dir.mkdir(parents=True, exist_ok=True)

            summary_dir = package_dir / "01_SUMMARY"
            models_dir = package_dir / "02_MODELS"
            snapshots_dir = package_dir / "03_SNAPSHOTS"

            summary_dir.mkdir(parents=True, exist_ok=True)
            models_dir.mkdir(parents=True, exist_ok=True)
            snapshots_dir.mkdir(parents=True, exist_ok=True)

            for file in project_dir.glob("*summary*"):
                if file.is_file():
                    target = summary_dir / file.name
                    target.write_bytes(file.read_bytes())

            deliverable_dir = project_dir / "deliverable"
            if deliverable_dir.exists():
                for file in deliverable_dir.iterdir():
                    if file.is_file():
                        target = models_dir / file.name
                        target.write_bytes(file.read_bytes())

            takeoffs_dir = project_dir / "takeoffs"
            if takeoffs_dir.exists():
                for template_dir in takeoffs_dir.iterdir():
                    if not template_dir.is_dir():
                        continue
                    latest_dir = template_dir / "latest"
                    if latest_dir.exists():
                        template_snapshot_dir = snapshots_dir / template_dir.name
                        template_snapshot_dir.mkdir(parents=True, exist_ok=True)
                        for path in latest_dir.rglob("*"):
                            if path.is_file():
                                relative = path.relative_to(latest_dir)
                                target = template_snapshot_dir / relative
                                target.parent.mkdir(parents=True, exist_ok=True)
                                target.write_bytes(path.read_bytes())

            print()
            print(f"PROJECT PACKAGE created at: {package_dir.resolve()}")
            print(f"summary_dir={summary_dir.resolve()}")
            print(f"models_dir={models_dir.resolve()}")
            print(f"snapshots_dir={snapshots_dir.resolve()}")
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



def _handle_templates(args: argparse.Namespace, *, db_path: Path) -> int:
    conn = SqliteDb(path=db_path).connect()
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



def _handle_template_lines(args: argparse.Namespace, *, db_path: Path) -> int:
    conn = SqliteDb(path=db_path).connect()
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



def _handle_takeoffs(args: argparse.Namespace, *, db_path: Path, config: AppConfig) -> int:
    conn = SqliteDb(path=db_path).connect()
    try:
        item_repo = SqliteItemRepository(conn=conn)
        project_repo = SqliteProjectRepository(conn=conn)
        project_fixture_override_repo = SqliteProjectFixtureOverrideRepository(conn=conn)
        template_repo = SqliteTemplateRepository(conn=conn)
        template_fixture_mapping_repo = SqliteTemplateFixtureMappingRepository(conn=conn)
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

        if args.takeoffs_cmd == "generate-from-plan":
            tax_rate: Decimal | None = None
            if args.tax_rate:
                tax_rate = _parse_decimal(args.tax_rate, "--tax-rate")

            use_case = GenerateTakeoffFromPlanReading(
                project_repo=project_repo,
                template_repo=template_repo,
                template_fixture_mapping_repo=template_fixture_mapping_repo,
                project_fixture_override_repo=project_fixture_override_repo,
                item_repo=item_repo,
                takeoff_repo=takeoff_repo,
                takeoff_line_repo=takeoff_line_repo,
            )

            plan = PlanReadingInput(
                stories=args.stories,
                kitchens=args.kitchens,
                garbage_disposals=args.garbage_disposals,
                laundry_rooms=args.laundry_rooms,
                lav_faucets=args.lav_faucets,
                toilets=args.toilets,
                showers=args.showers,
                bathtubs=args.bathtubs,
                half_baths=args.half_baths,
                double_bowl_vanities=args.double_bowl_vanities,
                hose_bibbs=args.hose_bibbs,
                ice_makers=args.ice_makers,
                water_heater_tank_qty=args.water_heater_tank_qty,
                water_heater_tankless_qty=args.water_heater_tankless_qty,
                sewer_distance_lf=args.sewer_distance_lf,
                water_distance_lf=args.water_distance_lf,
            )

            takeoff_id = use_case(
                project_code=args.project,
                template_code=args.template,
                plan=plan,
                tax_rate_override=tax_rate,
            )

            print(
                f"TAKEOFF generated id={takeoff_id} "
                f"project={args.project} template={args.template}"
            )
            return 0

        if args.takeoffs_cmd == "list":
            rows = takeoff_repo.list_for_project(project_code=args.project)
            for t in rows:
                print(
                    f"{t.takeoff_id} | project={t.project_code} | "
                    f"template={t.template_code} | "
                    f"tax_rate={t.tax_rate} | created_at={t.created_at} | valve_discount={t.valve_discount} | locked={t.is_locked}"
                )
            return 0

        if args.takeoffs_cmd == "show":
            t = takeoff_repo.get(takeoff_id=args.id)
            print(
                f"TAKEOFF {t.takeoff_id} | project={t.project_code} | template={t.template_code} | "
                f"tax_rate={t.tax_rate} | created_at={t.created_at} | valve_discount={t.valve_discount} | locked={t.is_locked}"
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

            gt = calc_grand_totals(
                inputs,
                valve_discount=t.valve_discount,
                tax_rate=t.tax_rate,
            )
            print(
                f"GRAND  | subtotal={gt.subtotal:.2f} | tax={gt.tax:.2f} | "
                f"total={gt.total:.2f} | valve_discount={gt.valve_discount:.2f} | "
                f"after_discount={gt.total_after_discount:.2f}"
            )
            return 0
        
        if args.takeoffs_cmd == "inspect":
            result = InspectTakeoff(
                takeoff_repo=takeoff_repo,
                takeoff_line_repo=takeoff_line_repo,
            )(takeoff_id=args.id)

            print("TAKEOFF INSPECT")
            print(f"id={result.takeoff_id}")
            print(f"project={result.project_code}")
            print(f"template={result.template_code}")
            print(f"locked={result.locked}")
            print(f"tax_rate={result.tax_rate}")
            print(f"valve_discount={result.valve_discount}")
            print()

            print("LINES")
            print(f"count={result.line_count}")
            print()

            print("STAGE TOTALS")
            for stage_name in ("ground", "topout", "final"):
                tt = result.stage_totals[stage_name]
                print(
                    f"{stage_name.upper():<6} | subtotal={tt.subtotal:.2f} | "
                    f"tax={tt.tax:.2f} | total={tt.total:.2f}"
                )
            print()

            gt = result.grand_totals
            print("GRAND TOTAL")
            print(f"subtotal={gt.subtotal:.2f}")
            print(f"tax={gt.tax:.2f}")
            print(f"total={gt.total:.2f}")
            print(f"valve_discount={gt.valve_discount:.2f}")
            print(f"after_discount={gt.total_after_discount:.2f}")
            print()

            print("VERSIONS")
            if not result.versions:
                print("none")
            else:
                for v in result.versions:
                    created_by = v.created_by or "-"
                    reason = v.reason or ""
                    print(
                        f"v{v.version_number} | {v.created_at} | "
                        f"created_by={created_by} | reason={reason} | version_id={v.version_id}"
                    )
            return 0

        if args.takeoffs_cmd == "add-line":
            item = item_repo.get(args.item)

            AddTakeoffLine(repo=takeoff_line_repo)(
                takeoff_id=args.id,
                item=item,
                qty=Decimal(args.qty),
                stage=Stage(args.stage),
                factor=Decimal(args.factor),
                sort_order=int(args.sort_order),
                notes=args.notes,
            )
            print(f"LINE added takeoff={args.id} item={item.code}")
            return 0

        if args.takeoffs_cmd == "update-line":
            target_kwargs: dict[str, object] = {}
            if args.line_id is not None:
                target_kwargs["line_id"] = args.line_id
                target_label = f"line_id={args.line_id}"
            else:
                target_kwargs["item_code"] = args.item
                target_label = f"item={args.item}"
            UpdateTakeoffLine(repo=takeoff_line_repo)(
                takeoff_id=args.id,
                **target_kwargs,
                qty=Decimal(args.qty) if args.qty else None,
                stage=Stage(args.stage) if args.stage else None,
                factor=Decimal(args.factor) if args.factor else None,
                sort_order=int(args.sort_order) if args.sort_order else None,
            )
            print(f"LINE updated takeoff={args.id} {target_label}")
            return 0

        if args.takeoffs_cmd == "delete-line":
            target_kwargs = {}
            if args.line_id is not None:
                target_kwargs["line_id"] = args.line_id
                target_label = f"line_id={args.line_id}"
            else:
                target_kwargs["item_code"] = args.item
                target_label = f"item={args.item}"
            DeleteTakeoffLine(repo=takeoff_line_repo)(
                takeoff_id=args.id,
                **target_kwargs,
            )
            print(f"LINE deleted takeoff={args.id} {target_label}")
            return 0

        if args.takeoffs_cmd == "lines":
            lines = list(
                ListTakeoffLines(repo=takeoff_line_repo)(takeoff_id=args.id)
            )
            for ln in lines:
                taxable = "taxable" if ln.taxable_snapshot else "non-taxable"
                stage = getattr(ln, "stage", None)
                stage_txt = stage.value if stage is not None else ""
                factor_txt = getattr(ln, "factor", "")
                sort_txt = getattr(ln, "sort_order", "")
                print(
                    f"line_id={getattr(ln, 'line_id', None)} | "
                    f"mapping_id={getattr(ln, 'mapping_id', None)} | "
                    f"item_code={ln.item_code} | qty={ln.qty} | stage={stage_txt} | "
                    f"factor={factor_txt} | sort_order={sort_txt} | "
                    f"description={ln.description_snapshot}"
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

        if args.takeoffs_cmd == "export-revision":
            out_dir = Path(args.out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            bundle_dir = ExportRevisionBundle(
                takeoff_repo=takeoff_repo,
                project_repo=project_repo,
                template_repo=template_repo,
                config=config,
            )(
                version_id=args.version_id,
                out_dir=out_dir,
            )

            print(f"REVISION bundle exported at: {bundle_dir.resolve()}")
            return 0

        if args.takeoffs_cmd == "verify-version":
            ok, expected_hash, actual_hash = takeoff_repo.verify_version_integrity(
                version_id=args.version_id
            )

            if ok:
                print(f"VERSION OK | version_id={args.version_id}")
                print(f"hash={actual_hash}")
                return 0

            print("VERSION INTEGRITY FAILED")
            print(f"version_id={args.version_id}")
            print(f"expected_hash={expected_hash}")
            print(f"actual_hash={actual_hash}")
            return 1

        if args.takeoffs_cmd == "revise":
            takeoff_repo.unlock(takeoff_id=args.id)
            print(f"TAKEOFF unlocked for revision id={args.id}")
            print()
            print("NEXT:")
            print(
                f"  python -m app.cli --db-path {args.db_path} takeoffs show --id {args.id}"
            )
            print(
                f"  python -m app.cli --db-path {args.db_path} takeoffs lines --id {args.id}"
            )
            return 0

        if args.takeoffs_cmd == "snapshot":
            version_id = takeoff_repo.create_snapshot_version(
                takeoff_id=args.id,
                notes=args.notes,
                created_by=args.created_by,
                reason=args.reason,
            )
            v = takeoff_repo.get_version(version_id=version_id)
            print(
                f"TAKEOFF snapshot created version_id={v.version_id} "
                f"takeoff_id={v.takeoff_id} v{v.version_number} created_at={v.created_at}"
            )
            if v.created_by or v.reason:
                print(
                    f"METADATA | created_by={v.created_by or '-'} | reason={v.reason or '-'}"
                )
            takeoff_repo.lock(takeoff_id=args.id)
            print()
            print("NEXT:")
            print(f"  python -m app.cli --db-path {args.db_path} takeoffs versions --id {v.takeoff_id}")
            print(
                "  python -m app.cli --db-path "
                f"{args.db_path} takeoffs render-version --version-id {v.version_id} "
                "--format pdf --out outputs/version.pdf"
            )
            return 0

        if args.takeoffs_cmd == "snapshot-and-render":
            fmt = OutputFormat(args.format)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)

            version_id = takeoff_repo.create_snapshot_version(
                takeoff_id=args.id,
                notes=args.notes,
                created_by=args.created_by,
                reason=args.reason,
            )
            v = takeoff_repo.get_version(version_id=version_id)

            rendered_path = RenderTakeoffFromVersion(
                project_repo=project_repo,
                template_repo=template_repo,
                takeoff_repo=takeoff_repo,
                renderer_factory=RendererRegistry(),
                config=config,
            )(
                version_id=version_id,
                out=out,
                fmt=fmt,
            )

            print(
                f"TAKEOFF snapshot created version_id={v.version_id} "
                f"takeoff_id={v.takeoff_id} v{v.version_number} created_at={v.created_at}"
            )
            if v.created_by or v.reason:
                print(
                    f"METADATA | created_by={v.created_by or '-'} | reason={v.reason or '-'}"
                )
            takeoff_repo.lock(takeoff_id=args.id)
            print(f"{fmt.value.upper()} generated at: {rendered_path.resolve()}")
            return 0

        if args.takeoffs_cmd in ("versions", "version"):
            rows = takeoff_repo.list_versions(takeoff_id=args.id)
            if not rows:
                print(f"No versions found for takeoff_id={args.id}")
                return 0
            for v in rows:
                notes = v.notes or ""
                created_by = v.created_by or ""
                reason = v.reason or ""
                print(
                    f"{v.version_id} | takeoff_id={v.takeoff_id} | "
                    f"v{v.version_number} | tax_rate={v.tax_rate_snapshot} | "
                    f"valve_discount={v.valve_discount_snapshot} | "
                    f"created_by={created_by} | reason={reason} | {v.created_at} | {notes}"
                )
            return 0

        if args.takeoffs_cmd == "history":
            t = takeoff_repo.get(takeoff_id=args.id)
            print(
                f"TAKEOFF HISTORY | takeoff_id={t.takeoff_id} | "
                f"project={t.project_code} | template={t.template_code}"
            )
            status = "locked" if t.is_locked else "unlocked"
            print(
                f"status={status} | tax_rate={t.tax_rate} | valve_discount={t.valve_discount}"
            )
            print()

            rows = takeoff_repo.list_versions(takeoff_id=args.id)
            if not rows:
                print("No snapshots created yet for this takeoff.")
                print()
                print("NEXT:")
                print(
                    f"  python -m app.cli --db-path {args.db_path} takeoffs snapshot --id {args.id}"
                )
                return 0

            for v in rows:
                created_by = v.created_by or "-"
                reason = v.reason or ""
                print(
                    f"v{v.version_number} | {v.created_at} | "
                    f"created_by={created_by} | reason={reason} | version_id={v.version_id}"
                )

            latest = rows[0]
            print()
            print("NEXT:")
            print(
                f"  python -m app.cli --db-path {args.db_path} takeoffs diff --v1 {latest.version_id} --v2 <other_version_id>"
            )
            print(
                f"  python -m app.cli --db-path {args.db_path} takeoffs render-version --version-id {latest.version_id} --format pdf --out outputs/version.pdf"
            )
            return 0

        if args.takeoffs_cmd == "revision-report":
            report = GenerateRevisionReport(takeoff_repo=takeoff_repo)(
                version_a=args.v1,
                version_b=args.v2,
            )
            text = report.to_text()

            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text, encoding="utf-8")
                print(f"REVISION REPORT generated at: {out.resolve()}")
            else:
                print(text, end="")
            return 0

        if args.takeoffs_cmd == "diff":
            result = DiffTakeoffVersions(takeoff_repo=takeoff_repo)(
                version_a=args.v1,
                version_b=args.v2,
            )

            if result.warnings:
                for warning in result.warnings:
                    print(f"WARNING | {warning}")
                print()

            visible = result.lines if args.all else tuple(
                ln for ln in result.lines if ln.change != "unchanged"
            )

            if not visible:
                print(
                    f"No differences found between version_a={result.version_a} "
                    f"and version_b={result.version_b}"
                )
                return 0

            summary = result.summary()
            print(
                "SUMMARY | "
                f"added={summary['added']} | "
                f"removed={summary['removed']} | "
                f"modified={summary['modified']} | "
                f"unchanged={summary['unchanged']}"
            )
            print(
                "FINANCIAL A | "
                f"subtotal={result.financial_a.subtotal:.2f} | "
                f"tax={result.financial_a.tax:.2f} | "
                f"total={result.financial_a.total:.2f} | "
                f"valve_discount={result.financial_a.valve_discount:.2f} | "
                f"after_discount={result.financial_a.total_after_discount:.2f}"
            )
            print(
                "FINANCIAL B | "
                f"subtotal={result.financial_b.subtotal:.2f} | "
                f"tax={result.financial_b.tax:.2f} | "
                f"total={result.financial_b.total:.2f} | "
                f"valve_discount={result.financial_b.valve_discount:.2f} | "
                f"after_discount={result.financial_b.total_after_discount:.2f}"
            )
            delta = result.financial_delta()
            print(
                "DELTA      | "
                f"subtotal={delta.subtotal:.2f} | "
                f"tax={delta.tax:.2f} | "
                f"total={delta.total:.2f} | "
                f"valve_discount={delta.valve_discount:.2f} | "
                f"after_discount={delta.total_after_discount:.2f}"
            )
            print()
            print(f"DIFF version_a={result.version_a} version_b={result.version_b}")
            for ln in visible:
                if ln.change == "added":
                    print(
                        f"{ln.item_code} | added | "
                        f"qty: - -> {ln.new.qty} | "
                        f"stage: - -> {ln.new.stage} | "
                        f"factor: - -> {ln.new.factor} | "
                        f"unit_price: - -> {ln.new.unit_price}"
                    )
                elif ln.change == "removed":
                    print(
                        f"{ln.item_code} | removed | "
                        f"qty: {ln.old.qty} -> - | "
                        f"stage: {ln.old.stage} -> - | "
                        f"factor: {ln.old.factor} -> - | "
                        f"unit_price: {ln.old.unit_price} -> -"
                    )
                elif ln.change == "modified":
                    print(
                        f"{ln.item_code} | modified | "
                        f"qty: {ln.old.qty} -> {ln.new.qty} | "
                        f"stage: {ln.old.stage} -> {ln.new.stage} | "
                        f"factor: {ln.old.factor} -> {ln.new.factor} | "
                        f"unit_price: {ln.old.unit_price} -> {ln.new.unit_price}"
                    )
                else:
                    print(
                        f"{ln.item_code} | unchanged | "
                        f"qty: {ln.old.qty} -> {ln.new.qty} | "
                        f"stage: {ln.old.stage} -> {ln.new.stage} | "
                        f"factor: {ln.old.factor} -> {ln.new.factor} | "
                        f"unit_price: {ln.old.unit_price} -> {ln.new.unit_price}"
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
                try:
                    _ = takeoff_repo.get(takeoff_id=args.version_id)
                except InvalidInputError:
                    raise
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
        # items (SQLite)
        # -------------------------
        items = sub.add_parser("items")
        items_sub = items.add_subparsers(dest="items_cmd", required=True)

        items_import = items_sub.add_parser("import")
        items_import.add_argument("--csv", required=True)

        items_add = items_sub.add_parser("add")
        items_add.add_argument("--code", required=True)
        items_add.add_argument("--description", required=True)
        items_add.add_argument("--unit-price", required=True)
        items_add.add_argument("--taxable", required=True)
        items_add.add_argument("--item-number", default=None)
        items_add.add_argument("--details", default=None)
        items_add.add_argument("--inactive", action="store_true")

        items_list = items_sub.add_parser("list")
        items_list.add_argument("--include-inactive", action="store_true")

        items_get = items_sub.add_parser("get")
        items_get.add_argument("--code", required=True)

        items_update = items_sub.add_parser("update")
        items_update.add_argument("--code", required=True)
        items_update.add_argument("--description", default=None)
        items_update.add_argument("--unit-price", default=None)
        items_update.add_argument("--taxable", default=None)
        items_update.add_argument("--item-number", default=None)
        items_update.add_argument("--details", default=None)
        items_update.add_argument("--clear-item-number", action="store_true")
        items_update.add_argument("--clear-details", action="store_true")

        items_activate = items_sub.add_parser("activate")
        items_activate.add_argument("--code", required=True)

        items_deactivate = items_sub.add_parser("deactivate")
        items_deactivate.add_argument("--code", required=True)

        # -------------------------
        # fixture-mappings (SQLite)
        # -------------------------
        fixture_mappings = sub.add_parser("fixture-mappings")
        fixture_mappings_sub = fixture_mappings.add_subparsers(dest="fm_cmd", required=True)

        fm_add = fixture_mappings_sub.add_parser("add")
        fm_add.add_argument("--template", required=True)
        fm_add.add_argument("--source-kind", choices=["derived", "plan", "constant"], required=True)
        fm_add.add_argument("--source-name", default=None)
        fm_add.add_argument("--constant-qty", default=None)
        fm_add.add_argument("--item", required=True)
        fm_add.add_argument("--qty-multiplier", default="1.0")
        fm_add.add_argument("--stage", choices=["ground", "topout", "final"], default="final")
        fm_add.add_argument("--factor", default="1.0")
        fm_add.add_argument("--sort-order", default="0")
        fm_add.add_argument("--notes", default=None)
        fm_add.add_argument("--inactive", action="store_true")
        fm_add.add_argument("--mapping-id", default=None)

        fm_list = fixture_mappings_sub.add_parser("list")
        fm_list.add_argument("--template", required=True)
        fm_list.add_argument("--include-inactive", action="store_true")

        fm_show = fixture_mappings_sub.add_parser("show")
        fm_show.add_argument("--mapping-id", required=True)

        fm_update = fixture_mappings_sub.add_parser("update")
        fm_update.add_argument("--mapping-id", required=True)
        fm_update.add_argument("--source-kind", choices=["derived", "plan", "constant"], default=None)
        fm_update.add_argument("--source-name", default=None)
        fm_update.add_argument("--constant-qty", default=None)
        fm_update.add_argument("--item", default=None)
        fm_update.add_argument("--qty-multiplier", default=None)
        fm_update.add_argument("--stage", choices=["ground", "topout", "final"], default=None)
        fm_update.add_argument("--factor", default=None)
        fm_update.add_argument("--sort-order", default=None)
        fm_update.add_argument("--notes", default=None)
        fm_update.add_argument("--clear-notes", action="store_true")

        fm_activate = fixture_mappings_sub.add_parser("activate")
        fm_activate.add_argument("--mapping-id", required=True)

        fm_deactivate = fixture_mappings_sub.add_parser("deactivate")
        fm_deactivate.add_argument("--mapping-id", required=True)

        # -------------------------
        # project-overrides (SQLite)
        # -------------------------
        project_overrides = sub.add_parser("project-overrides")
        project_overrides_sub = project_overrides.add_subparsers(dest="po_cmd", required=True)

        po_set = project_overrides_sub.add_parser("set")
        po_set.add_argument("--project", required=True)
        po_set.add_argument("--mapping-id", required=True)
        po_set.add_argument("--disable", action="store_true")
        po_set.add_argument("--item", default=None)
        po_set.add_argument("--notes", default=None)
        po_set.add_argument("--clear-item", action="store_true")
        po_set.add_argument("--clear-notes", action="store_true")

        po_list = project_overrides_sub.add_parser("list")
        po_list.add_argument("--project", required=True)

        po_show = project_overrides_sub.add_parser("show")
        po_show.add_argument("--project", required=True)
        po_show.add_argument("--mapping-id", required=True)

        po_delete = project_overrides_sub.add_parser("delete")
        po_delete.add_argument("--project", required=True)
        po_delete.add_argument("--mapping-id", required=True)

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

        p_summary = projects_sub.add_parser("summary")
        p_summary.add_argument("--code", required=True)

        p_invoice = projects_sub.add_parser("invoice")
        p_invoice.add_argument("--code", required=True)
        
        p_export = projects_sub.add_parser("export")
        p_export.add_argument("--code", required=True)
        p_export.add_argument("--out-dir", default="outputs")
        
        p_package = projects_sub.add_parser("package")
        p_package.add_argument("--code", required=True)
        p_package.add_argument("--out-dir", default="outputs")
        
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

        generate_from_plan = takeoffs_sub.add_parser("generate-from-plan")
        generate_from_plan.add_argument("--project", required=True)
        generate_from_plan.add_argument("--template", required=True)
        generate_from_plan.add_argument("--tax-rate", required=False)
        _add_plan_reading_args(generate_from_plan)

        lst = takeoffs_sub.add_parser("list")
        lst.add_argument("--project", required=True)

        show = takeoffs_sub.add_parser("show")
        show.add_argument("--id", required=True)
        
        inspect_cmd = takeoffs_sub.add_parser("inspect")
        inspect_cmd.add_argument("--id", required=True)

        lines_cmd = takeoffs_sub.add_parser("lines")
        lines_cmd.add_argument("--id", required=True)

        upd = takeoffs_sub.add_parser("update-line")
        upd.add_argument("--id", required=True)
        upd_target = upd.add_mutually_exclusive_group(required=True)
        upd_target.add_argument("--line-id", required=False)
        upd_target.add_argument("--item", required=False)
        upd.add_argument("--qty", required=False)
        upd.add_argument("--stage", choices=["ground", "topout", "final"], required=False)
        upd.add_argument("--factor", required=False)
        upd.add_argument("--sort-order", required=False)

        add_ln = takeoffs_sub.add_parser("add-line")
        add_ln.add_argument("--id", required=True)
        add_ln.add_argument("--item", required=True)
        add_ln.add_argument("--qty", required=True)
        add_ln.add_argument("--stage", choices=["ground", "topout", "final"], default="final")
        add_ln.add_argument("--factor", default="1.0")
        add_ln.add_argument("--sort-order", default="0")
        add_ln.add_argument("--notes", default=None)

        del_ln = takeoffs_sub.add_parser("delete-line")
        del_ln.add_argument("--id", required=True)
        del_target = del_ln.add_mutually_exclusive_group(required=True)
        del_target.add_argument("--line-id", required=False)
        del_target.add_argument("--item", required=False)

        revise = takeoffs_sub.add_parser("revise")
        revise.add_argument("--id", required=True)

        rnd = takeoffs_sub.add_parser("render")
        rnd.add_argument("--id", required=True)
        rnd.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
        rnd.add_argument("--out", required=True)
        
        snap = takeoffs_sub.add_parser("snapshot")
        snap.add_argument("--id", required=True)
        snap.add_argument("--notes", default=None)
        snap.add_argument("--created-by", default=None)
        snap.add_argument("--reason", default=None)

        vers = takeoffs_sub.add_parser("versions")
        vers.add_argument("--id", required=True)

        # Alias: version (singular)
        ver_alias = takeoffs_sub.add_parser("version")
        ver_alias.add_argument("--id", required=True)

        hist = takeoffs_sub.add_parser("history")
        hist.add_argument("--id", required=True)

        rv = takeoffs_sub.add_parser("render-version")
        rv.add_argument("--version-id", required=True)
        rv.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
        rv.add_argument("--out", required=True)

        snap_render = takeoffs_sub.add_parser("snapshot-and-render")
        snap_render.add_argument("--id", required=True)
        snap_render.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
        snap_render.add_argument("--out", required=True)
        snap_render.add_argument("--notes", default=None)
        snap_render.add_argument("--created-by", default=None)
        snap_render.add_argument("--reason", default=None)

        diff_cmd = takeoffs_sub.add_parser("diff")
        diff_cmd.add_argument("--v1", required=True)
        diff_cmd.add_argument("--v2", required=True)
        diff_cmd.add_argument("--all", action="store_true", help="Include unchanged lines")
        
        rev_report = takeoffs_sub.add_parser("revision-report")
        rev_report.add_argument("--v1", required=True)
        rev_report.add_argument("--v2", required=True)
        rev_report.add_argument("--out", required=False)

        export_rev = takeoffs_sub.add_parser("export-revision")
        export_rev.add_argument("--version-id", required=True)
        export_rev.add_argument("--out-dir", default="outputs")

        verify_version = takeoffs_sub.add_parser("verify-version")
        verify_version.add_argument("--version-id", required=True)

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
        # ITEMS (SQLite)
        # -------------------------
        if args.cmd == "items":
            return _handle_items(args, db_path=Path(args.db_path))

        # -------------------------
        # FIXTURE MAPPINGS (SQLite)
        # -------------------------
        if args.cmd == "fixture-mappings":
            return _handle_fixture_mappings(args, db_path=Path(args.db_path))

        # -------------------------
        # PROJECT OVERRIDES (SQLite)
        # -------------------------
        if args.cmd == "project-overrides":
            return _handle_project_overrides(args, db_path=Path(args.db_path))

        # -------------------------
        # PROJECTS (SQLite)
        # -------------------------
        if args.cmd == "projects":
            return _handle_projects(args, db_path=Path(args.db_path))

        # -------------------------
        # TEMPLATES (SQLite)
        # -------------------------
        if args.cmd == "templates":
            return _handle_templates(args, db_path=Path(args.db_path))

        # -------------------------
        # TEMPLATE LINES (SQLite)
        # -------------------------
        if args.cmd == "template-lines":
            return _handle_template_lines(args, db_path=Path(args.db_path))

        # -------------------------
        # TAKEOFFS (SQLite)
        # -------------------------
        if args.cmd == "takeoffs":
            return _handle_takeoffs(
                args,
                db_path=Path(args.db_path),
                config=config,
            )

        raise AssertionError("Unreachable: unknown command")

    except InvalidInputError as e:
        print(str(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
