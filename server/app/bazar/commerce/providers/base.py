"""Provider contract for the Santosh commerce layer.

Every offer is normalised to the same shape so the agent can compare across sources:
{source, ref, name, brand, price_paise, mrp_paise, pack, in_stock, max_qty, seller{name,key,city,network},
 delivery{}, returnable, return_window, cancellable, cod, country_of_origin, customer_care, image, url,
 buy_mode: "order" (Santosh completes it) | "handoff" (the user finishes on the store's own checkout), sponsored}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from ...db import CommerceCart, CommerceOrder, User


@dataclass
class QuoteResult:
    total_paise: int
    breakup: list[dict[str, Any]]                 # [{title, kind: item|delivery|packing|tax|discount|fee, amount_paise}]
    lines: list[dict[str, Any]]                   # cart lines with fresh prices
    disclosures: dict[str, Any] = field(default_factory=dict)
    payee_name: str = ""
    payee_vpa: str = ""                           # who the user's UPI payment goes to
    payment_mode: str = "upi_intent"              # upi_intent | handoff
    handoff_url: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaceResult:
    external_id: str
    status: str
    meta: dict[str, Any] = field(default_factory=dict)


class Provider(Protocol):
    source: str
    label: str

    def available(self) -> bool: ...
    def search(self, db: Session, user: User, query: str, pincode: str, limit: int) -> list[dict[str, Any]]: ...
    def quote(self, db: Session, user: User, cart: CommerceCart, address: dict[str, Any]) -> QuoteResult: ...
    def place(self, db: Session, user: User, order: CommerceOrder, payment_ref: str) -> PlaceResult: ...
    def status(self, db: Session, user: User, order: CommerceOrder) -> dict[str, Any]: ...
    def cancel(self, db: Session, user: User, order: CommerceOrder, reason_id: str) -> dict[str, Any]: ...
    def return_item(self, db: Session, user: User, order: CommerceOrder, item_ref: str, qty: int, reason_id: str,
                    reason: str) -> dict[str, Any]: ...


def words(text: str) -> list[str]:
    import re
    return [w for w in re.findall(r"[a-z0-9ऀ-ॿ]+", (text or "").lower()) if len(w) > 2]
