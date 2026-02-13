from __future__ import annotations

from pathlib import Path

import app.cli as cli


def _run(argv: list[str]) -> tuple[int | None, str]:
    try:
        rc = cli.main(argv)
        return rc, ""
    except SystemExit as e:
        msg = ""
        if e.args:
            msg = str(e.args[0])
        return None, msg


def test_save_json_requires_input_path() -> None:
    rc, msg = _run(["save", "--input", "json"])
    assert rc is None
    assert "--input-path is required when --input json is used" in msg


def test_save_input_path_only_allowed_with_json() -> None:
    rc, msg = _run(["save", "--input", "sample", "--input-path", "inputs/takeoff.json"])
    assert rc is None
    assert "--input-path can only be used with --input json" in msg


def test_save_input_path_must_exist() -> None:
    rc, msg = _run(
        [
            "save",
            "--input",
            "json",
            "--input-path",
            "inputs/does_not_exist.json",
        ]
    )
    assert rc is None
    assert "--input-path not found:" in msg


def test_save_repo_dir_cannot_be_empty() -> None:
    rc, msg = _run(["save", "--repo-dir", "   "])
    assert rc is None
    assert "--repo-dir cannot be empty" in msg


def test_save_success_sample(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    rc, msg = _run(["save", "--repo-dir", str(repo_dir)])
    assert msg == ""
    assert rc == 0
    assert repo_dir.exists()
    assert any(p.suffix == ".json" for p in repo_dir.iterdir())
