from __future__ import annotations

from pathlib import Path

import app.cli as cli


def _run(argv: list[str]) -> tuple[int | None, str]:
    try:
        rc = cli.main(argv)
        return rc, ""
    except SystemExit as e:
        msg = str(e.args[0]) if e.args else ""
        return None, msg


def test_read_only_blocks_mutating_command(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite"
    rc, msg = _run(
        [
            "--db-path",
            str(db_path),
            "--role",
            "read-only",
            "projects",
            "add",
            "--code",
            "PRJ-001",
            "--name",
            "Project 1",
            "--contractor",
            "Lennar",
            "--foreman",
            "John",
        ]
    )
    assert rc == 2
    assert msg == ""


def test_read_only_allows_non_mutating_command(tmp_path: Path) -> None:
    db_path = tmp_path / "db.sqlite"
    rc, msg = _run(
        [
            "--db-path",
            str(db_path),
            "--role",
            "read-only",
            "projects",
            "list",
        ]
    )
    assert msg == ""
    assert rc == 0
