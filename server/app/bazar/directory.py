"""MCP directory: ~50,700 MCP servers worldwide (npm, PyPI, awesome-mcp-servers, best-of lists, official reference servers).

A catalogue, not code Santosh runs. A server becomes usable when the user connects it: hosted ("cloud") servers by
their HTTPS MCP address; npm / PyPI packages run on a computer first (the user's PC or server), then its address is
added the same way. Rebuild with tools/build_mcp_directory.py.
"""
from __future__ import annotations

import gzip
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

FILE = Path(__file__).parent / "mcp_directory.json.gz"
STOP = {"the", "and", "for", "with", "from", "mcp", "server", "servers", "tool", "tools", "use", "using", "your", "kar",
        "karo", "ka", "ki", "ke", "hai", "mujhe", "chahiye", "wala", "wali", "ko", "se", "me", "mein", "aur", "koi", "do"}
# column positions in the file
N, SRC, NAME, LINK, FIELD, DOES, LANG, VER, REL, LIC, PRICE, OFFICIAL, REPO, DL, CAUTION = range(15)
SOURCE_LABEL = {"npm": "npm", "pypi": "PyPI", "awesome": "awesome-mcp-servers", "best-of": "best-of-mcp-servers",
                "reference": "Official MCP reference", "other": "Other"}


@lru_cache
def _data() -> dict[str, Any]:
    with gzip.open(FILE, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def servers() -> list[list]:
    return _data()["servers"]


@lru_cache
def _index() -> list[tuple[list, str, str, float]]:
    out = []
    for s in servers():
        prior = (3 if s[OFFICIAL] else 0) + (1 if s[PRICE] == "cloud" else 0) + min(5.0, math.log10(s[DL] + 1) * 1.2) \
            + (2 if s[SRC] in ("reference", "awesome", "best-of") else 0) - (2 if not s[DOES] else 0)
        out.append((s, s[NAME].lower(), f"{s[FIELD]} {s[DOES]} {s[REPO]}".lower(), prior))
    return out


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9.+-]*", text.lower()) if len(w) > 1 and w not in STOP]


_WA = re.compile(r"whats\s?app", re.I)
_WA_OK = re.compile(r"business (platform|api)|cloud api|whatsapp business api|meta (graph|cloud)", re.I)


def blocked(s: list) -> bool:
    """Unofficial personal-WhatsApp automation (WhatsApp Web / Baileys) breaks WhatsApp's terms and gets numbers banned.
    Santosh lists it but will not connect it; the official WhatsApp Business Platform is fine."""
    hay = f"{s[NAME]} {s[DOES]}"
    return bool(_WA.search(hay)) and not _WA_OK.search(hay)


def connect_mode(s: list) -> str:
    if s[PRICE] == "cloud":
        return "remote"
    if s[SRC] in ("npm", "pypi"):
        return "local"
    return "check"


def install_hint(s: list) -> str:
    if s[SRC] == "npm":
        return f"npx -y {s[NAME]}"
    if s[SRC] == "pypi":
        return f"uvx {s[NAME]}   (or: pip install {s[NAME]})"
    return ""


def public(s: list) -> dict[str, Any]:
    mode = connect_mode(s)
    how = {"remote": "Hosted service: add its MCP address (https://...) in Connect > MCP servers, or tell Santosh the address.",
           "local": "Package that runs on a computer: start it on your PC or server with an HTTP transport "
                    "(e.g. via an MCP gateway), then add that https address.",
           "check": "See the project page for how it runs, then add its https MCP address."}[mode]
    out: dict[str, Any] = {"ref": s[NAME], "name": s[NAME].split("/")[-1], "field": s[FIELD],
                           "does": s[DOES] or "(no description published)", "link": s[LINK], "github": s[REPO] or s[LINK],
                           "source": SOURCE_LABEL.get(s[SRC], s[SRC]), "official": s[OFFICIAL], "language": s[LANG],
                           "pricing": "Hosted service (account / API key likely)" if s[PRICE] == "cloud" else "Free / open source",
                           "connect": mode, "how_to_connect": how}
    for k, i in (("version", VER), ("released", REL), ("licence", LIC)):
        if s[i]:
            out[k] = s[i]
    if s[DL]:
        out["downloads_per_month"] = s[DL]
    if install_hint(s):
        out["install"] = install_hint(s)
    if blocked(s):
        out["connect"] = "not_allowed"
        out["how_to_connect"] = ("Santosh does not connect unofficial personal-WhatsApp automation (against WhatsApp's terms; "
                                 "numbers get banned). Use the official WhatsApp Business Platform instead.")
    if s[CAUTION]:
        out["caution"] = ("Can act on money, crypto, code or the computer. Santosh asks before every action; "
                          "only add it if you trust the publisher.")
    return out


def search(query: str, limit: int = 6, field: str = "") -> list[dict[str, Any]]:
    words = _words(query)
    fl = field.lower()
    if fl and not words:
        words = []
    scored = []
    for s, name, hay, prior in _index():
        if fl and fl != s[FIELD].lower():
            continue
        if words:
            sc = 0.0
            hit_all = True
            for w in words:
                inn, inh = w in name, w in hay
                if inn:
                    sc += 5
                if inh:
                    sc += 2
                if not (inn or inh):
                    hit_all = False
            if not sc:
                continue
            sc += (4 if hit_all else 0) + prior
        elif fl:
            sc = prior
        else:
            continue
        scored.append((sc, s))
    scored.sort(key=lambda x: (-x[0], x[1][NAME].lower()))
    return [public(s) for _, s in scored[:max(1, min(limit, 30))]]


@lru_cache
def _by_key() -> dict[str, list]:
    out: dict[str, list] = {}
    for s in servers():
        for k in (s[NAME].lower(), s[LINK].lower().rstrip("/"), s[REPO].lower().rstrip("/"), str(s[N])):
            if k and k not in out:
                out[k] = s
    return out


def get(ref: str) -> dict[str, Any] | None:
    """Raw entry as a dict with the keys custom_mcp expects (r = ref, d = description, f = field, c = caution, l = link)."""
    s = _by_key().get((ref or "").strip().lower().rstrip("/"))
    if s is None:
        return None
    return {"n": s[N], "r": s[NAME], "d": s[DOES], "f": s[FIELD], "c": s[CAUTION], "l": s[REPO] or s[LINK], "o": s[OFFICIAL],
            "blocked": blocked(s)}


def stats() -> dict[str, Any]:
    fields: dict[str, int] = {}
    sources: dict[str, int] = {}
    remote = 0
    for s in servers():
        fields[s[FIELD]] = fields.get(s[FIELD], 0) + 1
        lab = SOURCE_LABEL.get(s[SRC], s[SRC])
        sources[lab] = sources.get(lab, 0) + 1
        remote += s[PRICE] == "cloud"
    return {"total": len(servers()), "hosted": remote, "fields": dict(sorted(fields.items(), key=lambda x: -x[1])),
            "sources": sources, "source": _data()["source"]}
