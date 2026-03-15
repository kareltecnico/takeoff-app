from __future__ import annotations

from app.application.errors import AccessDeniedError
from app.domain.user_role import UserRole

_MUTATING_ACTIONS: set[tuple[str, str | None]] = {
    ("save", None),
    ("projects", "add"),
    ("projects", "set-valve-discount"),
    ("projects", "delete"),
    ("templates", "add"),
    ("templates", "delete"),
    ("template-lines", "add"),
    ("takeoffs", "seed"),
    ("takeoffs", "update-line"),
    ("takeoffs", "add-line"),
    ("takeoffs", "delete-line"),
    ("takeoffs", "revise"),
    ("takeoffs", "snapshot"),
    ("takeoffs", "snapshot-and-render"),
}


def authorize_command(*, role: UserRole, cmd: str, subcmd: str | None) -> None:
    if role == UserRole.ADMIN:
        return

    if (cmd, subcmd) in _MUTATING_ACTIONS or (cmd, None) in _MUTATING_ACTIONS:
        action = f"{cmd} {subcmd}" if subcmd else cmd
        raise AccessDeniedError(
            f"{role.value} role cannot run mutating action: {action}. "
            "Use --role admin for this command."
        )
