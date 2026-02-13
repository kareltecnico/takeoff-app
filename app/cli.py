from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from app.application.generate_takeoff_report_output import GenerateTakeoffReportOutput
from app.application.load_takeoff import LoadTakeoff
from app.application.save_takeoff import SaveTakeoff
from app.config import AppConfig
from app.domain.item import Item
from app.domain.stage import Stage
from app.domain.takeoff import Takeoff, TakeoffHeader
from app.domain.takeoff_line import TakeoffLine
from app.infrastructure.csv_takeoff_renderer import CsvTakeoffReportRenderer
from app.infrastructure.debug_takeoff_json_renderer import DebugJsonTakeoffReportRenderer
from app.infrastructure.file_takeoff_repository import FileTakeoffRepository
from app.infrastructure.pdf_takeoff_reportlab import ReportLabTakeoffPdfRenderer
from app.infrastructure.takeoff_json_loader import TakeoffJsonLoader
from app.reporting.renderers import TakeoffReportRenderer


def D(x: str) -> Decimal:
    return Decimal(x)


def _renderer_for(fmt: str) -> TakeoffReportRenderer:
    if fmt == "pdf":
        return ReportLabTakeoffPdfRenderer()
    if fmt == "json":
        return DebugJsonTakeoffReportRenderer()
    if fmt == "csv":
        return CsvTakeoffReportRenderer()
    raise SystemExit(f"Unknown format: {fmt!r}")


def _sample_takeoff() -> Takeoff:
    header = TakeoffHeader(
        project_name="TEST PROJECT",
        contractor_name="LENNAR",
        model_group_display="1331",
        stories=2,
        models=("1331",),
    )

    lines = (
        TakeoffLine(
            item=Item(
                code="WATER_HEATER_CONN",
                item_number="A100",
                description="Water heater connection",
                details="Sample line item",
                unit_price=D("250.00"),
                taxable=True,
            ),
            stage=Stage.GROUND,
            qty=D("1"),
            factor=D("1"),
            sort_order=1,
        ),
    )

    return Takeoff(header=header, tax_rate=D("0.07"), lines=lines)


def _require_non_empty(value: str | None, flag: str) -> str | None:
    if value is None:
        return None
    if not value.strip():
        raise SystemExit(f"{flag} cannot be empty")
    return value


def _parse_decimal(value: str, flag: str) -> Decimal:
    try:
        return D(value)
    except Exception as e:
        raise SystemExit(f"Invalid {flag}: {value!r}") from e


def _validate_out_extension(fmt: str, out: Path) -> None:
    expected = f".{fmt}"
    if out.suffix.lower() != expected:
        raise SystemExit(f"--out must end with {expected} for --format {fmt}")


def _validate_common_args(args: argparse.Namespace) -> None:
    # company name
    args.company_name = _require_non_empty(args.company_name, "--company-name")

    # output extension matches format
    out = Path(args.out)
    _validate_out_extension(args.format, out)

    # --id is exclusive (if you load from repo, don't mix it with input flags)
    if args.cmd == "render" and args.id:
        if args.input != "sample" or args.input_path:
            raise SystemExit(
                "--id cannot be combined with --input/--input-path. "
                "Use either --id or --input ... (json/sample)."
            )

    # validate input flags
    if args.input == "json":
        if not args.input_path:
            raise SystemExit("--input-path is required when --input json is used")
        p = Path(args.input_path)
        if not p.exists():
            raise SystemExit(f"--input-path not found: {p}")
    else:
        if args.input_path:
            raise SystemExit("--input-path can only be used with --input json")

    # validate tax override
    if args.tax_rate:
        if args.input != "sample":
            raise SystemExit("--tax-rate is only allowed with --input sample")
        tr = _parse_decimal(args.tax_rate, "--tax-rate")
        if tr < D("0") or tr > D("1"):
            raise SystemExit("--tax-rate must be between 0 and 1")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="takeoff-app")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # -------------------------
    # save
    # -------------------------
    save = sub.add_parser("save")
    save.add_argument(
        "--input",
        choices=["sample", "json"],
        default="sample",
        help="Input source: sample (built-in) or json (from file).",
    )
    save.add_argument(
        "--input-path",
        default=None,
        help="Path to JSON file (required when --input json).",
    )
    save.add_argument(
        "--repo-dir",
        default="data/takeoffs",
        help="Directory where takeoffs are stored.",
    )

    # -------------------------
    # render
    # -------------------------
    render = sub.add_parser("render")
    render.add_argument(
        "--input",
        choices=["sample", "json"],
        default="sample",
        help="Input source: sample (built-in) or json (from file).",
    )
    render.add_argument(
        "--input-path",
        default=None,
        help="Path to JSON file (required when --input json).",
    )
    render.add_argument(
        "--id",
        default=None,
        help="Load an already-saved takeoff by id (from repo).",
    )
    render.add_argument(
        "--repo-dir",
        default="data/takeoffs",
        help="Directory where takeoffs are stored.",
    )
    render.add_argument("--format", choices=["pdf", "json", "csv"], required=True)
    render.add_argument("--out", required=True)
    render.add_argument("--company-name", required=False)
    render.add_argument(
        "--tax-rate",
        required=False,
        help="Override tax rate for --input sample only (e.g. 0.07). Ignored for JSON/repo input.",
    )

    args = parser.parse_args(argv)

    # For both commands, validate things once (render uses --out/--format anyway)
    if args.cmd == "render":
        _validate_common_args(args)

    # repo + config used by commands
    repo = FileTakeoffRepository(base_dir=Path(args.repo_dir))
    company_name = getattr(args, "company_name", None) or AppConfig().company_name
    config = AppConfig(company_name=company_name)

    # -------------------------
    # save command
    # -------------------------
    if args.cmd == "save":
        repo_dir_raw = args.repo_dir
        if not repo_dir_raw or not str(repo_dir_raw).strip():
            raise SystemExit("--repo-dir cannot be empty")

        # ---- validate input flags ----
        if args.input == "json":
            if not args.input_path:
                raise SystemExit("--input-path is required when --input json is used")
            p = Path(args.input_path)
            if not p.exists():
                raise SystemExit(f"--input-path not found: {p}")
        else:
            if args.input_path:
                raise SystemExit("--input-path can only be used with --input json")

        # ---- build takeoff once ----
        if args.input == "json":
            takeoff = TakeoffJsonLoader().load(Path(args.input_path))
        else:
            takeoff = _sample_takeoff()

        stored = SaveTakeoff(repo=repo)(takeoff)
        print(f"SAVED takeoff id={stored.id} path={stored.path.resolve()}")
        return 0

    # -------------------------
    # render command
    # -------------------------
    if args.cmd == "render":
        fmt: str = args.format
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)

        renderer = _renderer_for(fmt)
        use_case = GenerateTakeoffReportOutput(renderer=renderer, config=config)

        # Build takeoff exactly once
        if args.id:
            takeoff = LoadTakeoff(repo=repo)(args.id)
        elif args.input == "json":
            takeoff = TakeoffJsonLoader().load(Path(args.input_path))
        else:
            takeoff = _sample_takeoff()
            if args.tax_rate:
                takeoff = Takeoff(
                    header=takeoff.header,
                    tax_rate=_parse_decimal(args.tax_rate, "--tax-rate"),
                    lines=takeoff.lines,
                )

        use_case(takeoff, out)
        print(f"{fmt.upper()} generated at: {out.resolve()}")
        return 0

    raise SystemExit(f"Unknown command: {args.cmd!r}")


if __name__ == "__main__":
    raise SystemExit(main())