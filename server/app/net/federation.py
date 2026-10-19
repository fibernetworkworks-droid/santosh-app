"""Hoola avatars on other servers (v0.34)."""
from __future__ import annotations

from typing import Any


def send(env: dict[str, Any]) -> dict[str, Any]:
    return {"ok": False, "status": "refused", "reason": "Doosre server ke Hoola se judna abhi chalu nahi hai."}


def lookup(handle: str, dom: str) -> str:
    from .service import NetError
    raise NetError("Doosre server ke Hoola se judna abhi chalu nahi hai.")
