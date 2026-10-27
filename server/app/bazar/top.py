"""The plugins people use every day, shown first on the Connect tab ("Roz ke kaam").

A fixed, hand-picked order per section (what most Indian phones open daily), then the owner's own: plugins she already
linked or used rise to the front of their section. Electricity follows her pincode (MSEDCL, Adani, Tata Power, Torrent,
Goa...). Only packs that exist in the registry are shown; nothing here changes what a plugin is allowed to do.
"""
from __future__ import annotations

from typing import Any

SECTIONS: list[tuple[str, str, str, list[str]]] = [
    # (id, title, icon hint, pack ids in order)
    ("pay", "Paisa bhejo", "payments", ["google-pay", "phonepe", "paytm", "bhim", "amazon-pay-upi", "cred-upi"]),
    ("food", "Khana aur kirana", "food", ["swiggy-food", "zomato", "swiggy-instamart", "zepto", "swiggy-dineout", "jiomart-digital"]),
    ("ride", "Safar", "ride", ["uber-india", "ola", "rapido", "irctc-rail-connect", "redbus", "makemytrip"]),
    ("bills", "Bill aur recharge", "bills", ["@electricity", "jio", "airtel", "vi-vodafone-idea", "indane-lpg-booking",
                                             "hp-gas-booking", "jiofiber-airfiber", "@fastag"]),
    ("shop", "Shopping", "shop", ["amazon-india", "flipkart", "jiomart-digital", "porter"]),
    ("health", "Sehat aur sarkari", "health", ["tata-1mg", "pharmeasy", "practo", "apollo-24-7", "digilocker", "umang", "epfo"]),
    ("money", "Bank aur nivesh", "money", ["hdfc-bank", "icici-bank", "axis-bank", "kotak-mahindra-bank", "groww", "zerodha-kite"]),
]
PER_SECTION = 8


def electricity_for(pincode: str) -> str:
    """The state / city power board for an Indian pincode ('' when not known)."""
    p = "".join(ch for ch in str(pincode or "") if ch.isdigit())
    if len(p) != 6:
        return "msedcl-mahavitaran"           # Hoola's home state by default
    if p[:3] == "403":
        return "goa-electricity-dept"
    if p[:3] in ("400", "401"):
        return "adani-electricity-mumbai"
    if p[:2] in ("40", "41", "42", "43", "44"):
        return "msedcl-mahavitaran"
    if p[:2] in ("38", "39"):
        return "torrent-power"
    if p[:2] == "11":
        return "tata-power-ddl"
    if p[:3] == "160":
        return "chandigarh-electricity"
    if p[:3] == "605":
        return "puducherry-electricity"
    return ""


def fastag_for(linked_banks: set[str]) -> str:
    for bank, tag in (("hdfc-bank", "hdfc-fastag"), ("icici-bank", "icici-fastag"), ("axis-bank", "axis-fastag"),
                      ("kotak-mahindra-bank", "kotak-fastag")):
        if bank in linked_banks:
            return tag
    return "paytm-fastag"


def sections(packs: list[dict[str, Any]], pincode: str = "", used: dict[str, int] | None = None) -> list[dict[str, Any]]:
    """[{id, title, icon, items: [pack dict...]}] in display order."""
    by_id = {p["pack_id"]: p for p in packs}
    used = used or {}
    linked = {p["pack_id"] for p in packs if p.get("status") == "ready" and p.get("executor") in ("mcp",)}
    out = []
    seen: set[str] = set()
    for sid, title, icon, ids in SECTIONS:
        items = []
        for i, pid in enumerate(ids):
            if pid == "@electricity":
                pid = electricity_for(pincode)
            elif pid == "@fastag":
                pid = fastag_for(set(used))
            p = by_id.get(pid)
            if p is None or pid in seen:
                continue
            seen.add(pid)
            rank = (0 if pid in linked else 1, -used.get(pid, 0), i)
            items.append((rank, p))
        items.sort(key=lambda x: x[0])
        if items:
            out.append({"id": sid, "title": title, "icon": icon, "items": [p for _, p in items[:PER_SECTION]]})
    return out
