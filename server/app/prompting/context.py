"""What Hoola already knows about her business, for filling a brief. Read-only and fail-open: a store that cannot be
read is simply not used. Nothing here is a secret: the brand kit's public fields and her own memory page."""
from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("santosh.prompting")


def known(tenant: str) -> dict[str, Any]:
    out: dict[str, Any] = {"name": "", "tagline": "", "colours": [], "tone": "", "language": "", "about": "", "items": []}
    try:
        from ..brand import service as BS
        k = BS.kit(tenant)
        out["name"], out["tagline"] = str(k.get("name") or ""), str(k.get("tagline") or "")
        out["tone"], out["language"] = str(k.get("tone") or ""), str(k.get("language") or "")
        if k.get("colors_set"):
            cols = k.get("colors") or {}
            out["colours"] = [str(v) for v in (cols.values() if isinstance(cols, dict) else cols) if v][:4]
    except Exception:       # noqa: BLE001
        log.debug("prompting: brand kit not readable", exc_info=True)
    try:
        from .. import aboutme
        out["about"] = str(aboutme.get(tenant).get("text") or "")[:1200]
    except Exception:       # noqa: BLE001
        log.debug("prompting: memory page not readable", exc_info=True)
    for label, key in (("Business name", "name"), ("Tagline", "tagline"), ("Brand tone", "tone")):
        if out[key]:
            out["items"].append({"label": label, "value": out[key]})
    if out["colours"]:
        out["items"].append({"label": "Brand colours", "value": ", ".join(out["colours"])})
    if out["about"]:
        out["items"].append({"label": "Hoola's notes about you", "value": out["about"][:240]})
    return out


def fill(section: str, k: dict[str, Any]) -> dict[str, str]:
    """Slots her own business details can fill with certainty (labelled 'from your business' on the page)."""
    out: dict[str, str] = {}
    name = k.get("name") or ""
    if section == "web" and name:
        out["what"] = name + (f" - {k['tagline']}" if k.get("tagline") else "")
    if section == "image" and k.get("colours"):
        out["colours"] = "brand colours " + ", ".join(k["colours"])
    if section == "script" and k.get("tone"):
        out["tone"] = k["tone"]
    return out
