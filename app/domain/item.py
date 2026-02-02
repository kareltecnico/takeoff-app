from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Item:
    """
    Master catalog item.
    """
    code: str                 # internal stable code (e.g. KITCH_FAUCET_STD)
    item_number: str | None   # Lennar item number (can change / be None)
    description: str          # short name
    details: str | None       # brand / model / finish
    unit_price: Decimal
    taxable: bool
    is_active: bool = True
