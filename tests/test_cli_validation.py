from __future__ import annotations

from pathlib import Path

import pytest

from app.cli import main


def test_out_extension_must_match_format(tmp_path: Path) -> None:
    out = tmp_path / "x.json"
    with pytest.raises(SystemExit):
        main(["render", "--format", "pdf", "--out", str(out)])


def test_tax_rate_only_allowed_for_sample(tmp_path: Path) -> None:
    out = tmp_path / "x.pdf"
    with pytest.raises(SystemExit):
        main(
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
                str(out),
            ]
        )
