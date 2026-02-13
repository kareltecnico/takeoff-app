from __future__ import annotations

from pathlib import Path

import app.cli as cli


def _run(argv: list[str]) -> tuple[int | None, str]:
    """
    Run cli.main(argv) and return:
      (exit_code_if_normal_return_else_None, captured_message_if_SystemExit)
    """
    try:
        rc = cli.main(argv)
        return rc, ""
    except SystemExit as e:
        msg = ""
        if e.args:
            msg = str(e.args[0])
        return None, msg


def test_render_out_extension_must_match_format() -> None:
    rc, msg = _run(["render", "--format", "pdf", "--out", "outputs/result.json"])
    assert rc is None
    assert "--out must end with .pdf" in msg


def test_render_company_name_cannot_be_empty() -> None:
    rc, msg = _run(
        [
            "render",
            "--format",
            "pdf",
            "--out",
            "outputs/result.pdf",
            "--company-name",
            "   ",
        ]
    )
    assert rc is None
    assert "--company-name cannot be empty" in msg


def test_render_input_json_requires_input_path() -> None:
    rc, msg = _run(
        ["render", "--input", "json", "--format", "pdf", "--out", "outputs/result.pdf"]
    )
    assert rc is None
    assert "--input-path is required when --input json is used" in msg


def test_render_input_path_only_allowed_with_input_json() -> None:
    rc, msg = _run(
        [
            "render",
            "--input",
            "sample",
            "--input-path",
            "inputs/takeoff.json",
            "--format",
            "pdf",
            "--out",
            "outputs/result.pdf",
        ]
    )
    assert rc is None
    assert "--input-path can only be used with --input json" in msg


def test_render_input_path_must_exist() -> None:
    rc, msg = _run(
        [
            "render",
            "--input",
            "json",
            "--input-path",
            "inputs/does_not_exist.json",
            "--format",
            "pdf",
            "--out",
            "outputs/result.pdf",
        ]
    )
    assert rc is None
    assert "--input-path not found:" in msg


def test_render_tax_rate_only_allowed_with_sample() -> None:
    rc, msg = _run(
        [
            "render",
            "--input",
            "json",
            "--input-path",
            "inputs/takeoff.json",
            "--tax-rate",
            "0.07",
            "--format",
            "pdf",
            "--out",
            "outputs/result.pdf",
        ]
    )
    assert rc is None
    assert "--tax-rate is only allowed with --input sample" in msg


def test_render_tax_rate_must_be_decimal() -> None:
    rc, msg = _run(
        [
            "render",
            "--input",
            "sample",
            "--tax-rate",
            "abc",
            "--format",
            "pdf",
            "--out",
            "outputs/result.pdf",
        ]
    )
    assert rc is None
    assert "Invalid --tax-rate" in msg


def test_render_tax_rate_must_be_between_0_and_1() -> None:
    rc, msg = _run(
        [
            "render",
            "--input",
            "sample",
            "--tax-rate",
            "1.5",
            "--format",
            "pdf",
            "--out",
            "outputs/result.pdf",
        ]
    )
    assert rc is None
    assert "--tax-rate must be between 0 and 1" in msg


def test_render_id_cannot_be_combined_with_input_flags() -> None:
    rc, msg = _run(
        [
            "render",
            "--id",
            "abc123",
            "--input",
            "json",
            "--input-path",
            "inputs/takeoff.json",
            "--format",
            "pdf",
            "--out",
            "outputs/result.pdf",
        ]
    )
    assert rc is None
    assert "--id cannot be combined with --input/--input-path" in msg


def test_render_accepts_valid_args_smoke(tmp_path: Path) -> None:
    out = tmp_path / "ok.pdf"
    rc, msg = _run(["render", "--format", "pdf", "--out", str(out)])
    assert msg == ""
    assert rc == 0
    assert out.exists()
