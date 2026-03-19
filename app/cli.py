from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path
import json
import re

from app.application.build_sample_takeoff import BuildSampleTakeoff
from app.application.errors import InvalidInputError
from app.application.generate_revision_report import GenerateRevisionReport
from app.application.export_revision_bundle import ExportRevisionBundle
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
from app.application.diff_takeoff_versions import DiffTakeoffVersions
from app.application.seed_takeoff_from_template import SeedTakeoffFromTemplate
from app.application.add_takeoff_line import AddTakeoffLine
from app.application.delete_takeoff_line import DeleteTakeoffLine
from app.application.list_takeoff_lines import ListTakeoffLines
from app.application.update_takeoff_line import UpdateTakeoffLine
from app.application.inspect_takeoff import InspectTakeoff
from app.application.summarize_project import SummarizeProject
from app.application.generate_project_invoice import GenerateProjectInvoice
from app.config import AppConfig
from app.domain.output_format import OutputFormat
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
            UpdateTakeoffLine(repo=takeoff_line_repo)(
                takeoff_id=args.id,
                item_code=args.item,
                qty=Decimal(args.qty) if args.qty else None,
                stage=Stage(args.stage) if args.stage else None,
                factor=Decimal(args.factor) if args.factor else None,
                sort_order=int(args.sort_order) if args.sort_order else None,
            )
            print(f"LINE updated takeoff={args.id} item={args.item}")
            return 0

        if args.takeoffs_cmd == "delete-line":
            DeleteTakeoffLine(repo=takeoff_line_repo)(
                takeoff_id=args.id,
                item_code=args.item,
            )
            print(f"LINE deleted takeoff={args.id} item={args.item}")
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
                    f"{ln.item_code} | qty={ln.qty} | stage={stage_txt} | "
                    f"factor={factor_txt} | sort_order={sort_txt} | {taxable} | "
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
        upd.add_argument("--item", required=True)
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
        del_ln.add_argument("--item", required=True)

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
