
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """
    Central application configuration.

    export_root:
        Primary local folder where generated artifacts are written.

    mirror_export_root:
        Optional secondary folder (e.g. network share) where a copy of
        exported revision bundles is also written. If None, mirroring
        is disabled.
    """

    company_name: str = "LEZA'S PLUMBING"
    default_tax_rate: Decimal = Decimal("0.07")

    # Export configuration
    export_root: Path = Path("outputs")

    # Optional mirror location (ex: network drive)
    mirror_export_root: Path | None = None
