"""v0.999.112 ULTIMATE PC PLAN P2 - SAFETY in code, on both PCs (docs/HOOLA_ULTIMATE_PC_PLAN.md).

Four rules that no model output can talk its way past:
1. HER RULES: sites Hoola must never open, sites where every change asks her first (even inside a repeat job she
   approved), and her own sentences read as rules by the PC worker. Stored per person (data/pc_rules/<tenant>.json),
   GET / PUT /api/pc/rules; the Watch page (P6) gets the editor.
2. AN APPROVAL IS FOR THE PAGE SHE SAW: her yes covers the next few steps only while the job stays on the same site;
   when the page moves to another site, the next risky step asks again.
3. A PASSWORD GOES ONLY WHERE IT WAS ASKED FOR: the private sign-in form remembers the site it was opened for; if the
   page in front is another site when her sign-in arrives, nothing is typed.
4. DATA LEAVING HOOLA PC: a shell command that would send files or form data to the internet (curl -d / -F / -T,
   wget --post, scp, rsync to a remote, ftp, nc, mail...) asks her first; downloads and reads stay free.
Everything here is pure: the operator and hands.py call it; it never acts by itself."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel

MAX_SITES = 100
MAX_NOTES = 20


def _dir() -> Path:
    return Path(os.environ.get("PC_RULES_DIR", "data/pc_rules"))


def _file(tenant: str) -> Path:
    return _dir() / (re.sub(r"[^A-Za-z0-9_.-]", "_", str(tenant or "default"))[:64] + ".json")


def host_of(url: str) -> str:
    try:
        h = (urlparse(str(url or "")).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _clean_site(s: str) -> str:
    s = str(s or "").strip().lower()
    if "://" in s:
        s = host_of(s)
    s = s.split("/")[0].lstrip("*.").removeprefix("www.")
    return s if re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", s) else ""


def get(tenant: str) -> dict[str, Any]:
    try:
        d = json.loads(_file(tenant).read_text())
    except (OSError, ValueError):
        d = {}
    return {"never": list(d.get("never") or []), "ask": list(d.get("ask") or []), "notes": list(d.get("notes") or []),
            "updated": d.get("updated")}


def save(tenant: str, rules: dict[str, Any]) -> dict[str, Any]:
    def sites(xs):
        out = []
        for x in (xs or [])[:MAX_SITES]:
            c = _clean_site(x)
            if c and c not in out:
                out.append(c)
        return out
    clean = {"never": sites(rules.get("never")), "ask": sites(rules.get("ask")),
             "notes": [str(n).strip()[:200] for n in (rules.get("notes") or []) if str(n).strip()][:MAX_NOTES],
             "updated": int(time.time())}
    _dir().mkdir(parents=True, exist_ok=True)
    _file(tenant).write_text(json.dumps(clean, indent=1))
    return clean


def _on(host: str, sites: list[str]) -> str:
    """The rule that covers this host (the site itself or any page under it), or ''."""
    host = str(host or "").lower()
    for s in sites:
        if host == s or host.endswith("." + s):
            return s
    return ""


def blocked_open(tenant: str, url: str) -> str:
    """A site on her never-list: the reason, else ''."""
    s = _on(host_of(url), get(tenant)["never"])
    return f"{s} is on her list of sites Hoola must never open" if s else ""


def must_ask(tenant: str, cur_url: str) -> str:
    """A site where every change asks her first: the reason, else ''."""
    s = _on(host_of(cur_url), get(tenant)["ask"])
    return f"on {s} every change asks her first (her rule)" if s else ""


def prompt_block(tenant: str) -> str:
    r = get(tenant)
    if not (r["never"] or r["ask"] or r["notes"]):
        return ""
    lines = ["\nHER RULES (she set them; the system also enforces the site rules in code):"]
    if r["never"]:
        lines.append("- Never open: " + ", ".join(r["never"]))
    if r["ask"]:
        lines.append("- Ask her before any change on: " + ", ".join(r["ask"]))
    lines += [f"- {n}" for n in r["notes"]]
    return "\n".join(lines)


def same_site(a: str, b: str) -> bool:
    ha, hb = host_of(a), host_of(b)
    return bool(ha) and ha == hb


# data leaving the PC: a command that UPLOADS / SENDS (a download or a read is free)
_EGRESS = re.compile(
    r"\bcurl\b[^|;&]*\s(-d|--data\S*|-F|--form\S*|-T|--upload-file|-X\s*(POST|PUT|PATCH))\b"
    r"|\bwget\b[^|;&]*--(post-data|post-file|body-data|body-file|method=(POST|PUT))"
    r"|\b(scp|sftp|ftp|lftp|ncftp|smbclient|sendmail|mutt|mailx?|swaks)\b"
    r"|\brsync\b[^|;&]*\s\S+@?\S*:\S*"
    r"|\b(nc|ncat|netcat|socat|telnet)\b"
    r"|\b(rclone|aws|gsutil|azcopy)\b\s+(copy|cp|sync|move|mv)\b"
    r"|requests\.(post|put|patch)|urllib\.request\.urlopen\([^)]*data=|httpx\.(post|put|patch)",
    re.I)


def egress(cmd: str) -> str:
    """The reason a command sends data out of the PC, else ''."""
    m = _EGRESS.search(str(cmd or ""))
    return f"this command sends data out of the PC ({m.group(0).strip()[:60]})" if m else ""


class Rules(BaseModel):
    never: list[str] = []
    ask: list[str] = []
    notes: list[str] = []


def mount(app, current_tenant, require_key) -> None:
    from fastapi import APIRouter, Depends

    r = APIRouter(prefix="/api/pc/rules", dependencies=[Depends(require_key)])

    @r.get("")
    def rules_get(tenant: str = Depends(current_tenant)):
        return get(tenant)

    @r.put("")
    def rules_put(body: Rules, tenant: str = Depends(current_tenant)):
        return save(tenant, body.model_dump())

    app.include_router(r)
