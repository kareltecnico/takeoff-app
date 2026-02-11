from __future__ import annotations

from pathlib import Path

import pytest

from app.cli import main


def test_cli_render_sample_pdf_creates_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "sample.pdf"
    rc = main(["render", "--format", "pdf", "--out", str(out)])

    assert rc == 0
    assert out.exists()
    captured = capsys.readouterr().out
    assert "PDF generated at:" in captured


def test_cli_render_json_input_requires_input_path(tmp_path: Path) -> None:
    out = tmp_path / "x.pdf"
    with pytest.raises(SystemExit):
        main(["render", "--input", "json", "--format", "pdf", "--out", str(out)])


def test_cli_render_json_input_pdf(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Minimal valid JSON
    json_path = tmp_path / "takeoff.json"
    json_path.write_text(
        """
{
  "header": {
    "project_name": "TEST",
    "contractor_name": "LENNAR",
    "model_group_display": "1331",
    "stories": 2,
    "models": ["1331"]
  },
  "tax_rate": "0.07",
  "lines": [
    {
      "stage": "GROUND",
      "qty": "1",
      "factor": "1",
      "sort_order": 1,
      "item": {
        "code": "A",
        "item_number": "A100",
        "description": "Desc",
        "unit_price": "100.00",
        "taxable": true
      }
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    out = tmp_path / "result.pdf"
    rc = main(
        [
            "render",
            "--input",
            "json",
            "--input-path",
            str(json_path),
            "--format",
            "pdf",
            "--out",
            str(out),
        ]
    )

    assert rc == 0
    assert out.exists()
    captured = capsys.readouterr().out
    assert "PDF generated at:" in captured
