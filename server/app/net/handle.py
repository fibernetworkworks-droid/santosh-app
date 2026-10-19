"""'Tum sambhalo': the avatar handles a request or a thread on its own, within the owner's rules (v0.30)."""
from __future__ import annotations

from typing import Any


def maybe_handle(tenant: str, m, rules: dict[str, Any], link, card: dict[str, Any]) -> bool:
    return False


def continue_thread(tenant: str, m, who: str) -> bool:
    return False


def take_over(tenant: str, m, note: str = "") -> dict[str, Any]:
    from .service import NetError
    raise NetError("Yeh suvidha jaldi aa rahi hai.")
