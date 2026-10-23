"""MCP directory: ~63,700 MCP servers worldwide (npm, PyPI, awesome / best-of lists, the official reference servers,
mcp.so, mcpservers.org and the Apify Store), merged so one server is listed once.

Every entry has a clean display name, a short description (<= 140 characters), a category, its publisher and an HD logo
(the brand's own site, the listing's own picture, the publisher's GitHub organisation, else a drawn monogram tile).
A catalogue, not code Santosh runs. A server becomes usable when the user connects it: hosted ("cloud") servers by their
HTTPS MCP address; npm / PyPI packages run on a computer first, then their address is added the same way.
Rebuild with tools/merge_mcp_lists.py (v2; the v1 builder is tools/build_mcp_directory.py).
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
# column positions in the file (v1 = the first 15; v2 adds the rest)
(N, SRC, NAME, LINK, FIELD, DOES, LANG, VER, REL, LIC, PRICE, OFFICIAL, REPO, DL, CAUTION, TITLE, SHORT, BY, LOGO, HOME,
 MCP_URL, VERIFIED, FEATURED, USERS, ALIASES, ID, BLOCKED, TAGS, SOURCES) = range(29)
SOURCE_LABEL = {"npm": "npm", "pypi": "PyPI", "awesome": "awesome-mcp-servers", "best-of": "best-of-mcp-servers",
                "reference": "Official MCP reference", "mcpso": "mcp.so", "mso": "mcpservers.org", "apify": "Apify Store",
                "other": "Other"}
LOGO_VERSION = "3"
_ID = re.compile(r"^[0-9a-f]{10}$")


@lru_cache
def _data() -> dict[str, Any]:
    with gzip.open(FILE, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("version") != 2:   # an old v1 file: give every row the v2 columns so the rest of the code is one path
        for s in data["servers"]:
            s += [""] * (29 - len(s))
            s[TITLE], s[SHORT], s[LOGO], s[ALIASES], s[TAGS], s[SOURCES] = s[NAME], s[DOES], ["", "", "", 0], [], [], [s[SRC]]
            s[ID] = f"{s[N]:010x}"[-10:]
    return data


def servers() -> list[list]:
    return _data()["servers"]


def categories() -> list[str]:
    return _data().get("categories") or sorted({s[FIELD] for s in servers()})


@lru_cache
def _index() -> list[tuple[list, str, str, float]]:
    out = []
    for s in servers():
        prior = (3 if s[OFFICIAL] else 0) + (1.5 if s[VERIFIED] else 0) + (1.5 if s[FEATURED] else 0) \
            + (1 if s[PRICE] == "cloud" else 0) + (1 if s[MCP_URL] else 0) + min(5.0, math.log10(s[DL] + 1) * 1.2) \
            + min(2.0, math.log10((s[USERS] or 0) + 1)) + (2 if s[SRC] in ("reference", "awesome", "best-of") else 0) \
            + 0.5 * (len(s[SOURCES]) - 1) - (1 if s[BLOCKED] else 0)
        name = f"{s[TITLE]} {s[NAME]}".lower()
        hay = f"{s[FIELD]} {s[SHORT]} {s[DOES]} {s[REPO]} {s[BY]} {' '.join(s[TAGS])}".lower()
        out.append((s, name, hay, prior))
    return out


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9.+-]*", text.lower()) if len(w) > 1 and w not in STOP]


_WA = re.compile(r"whats\s?app", re.I)
_WA_OK = re.compile(r"business (platform|api)|cloud api|whatsapp business api|meta (graph|cloud)", re.I)


_RE = re.compile(r"reverse[- ]?engineer|decompil|disassembl|binary analysis|\bghidra\b|\bida pro\b|\bfrida\b|"
                 r"\bhopper\b|packet capture|\bpcap\b|jailbreak|crack", re.I)


def risky(s: list) -> bool:
    return bool(s[CAUTION]) or bool(_RE.search(f"{s[NAME]} {s[TITLE]} {s[DOES]} {s[SHORT]}"))


def blocked(s: list) -> str:
    """'' = may be connected. 'whatsapp' = unofficial personal-WhatsApp automation (WhatsApp Web / Baileys: against
    WhatsApp's terms, numbers get banned; the official WhatsApp Business Platform is fine). 'scraper' = an Apify actor
    that scrapes other people's sites (Hoola uses official routes only)."""
    if s[BLOCKED]:
        return s[BLOCKED]
    hay = f"{s[NAME]} {s[TITLE]} {s[DOES]} {s[SHORT]}"
    return "whatsapp" if _WA.search(hay) and not _WA_OK.search(hay) else ""


def connect_mode(s: list) -> str:
    if s[MCP_URL] or (s[PRICE] == "cloud" and s[SRC] != "apify"):
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


def logo_path(s: list) -> str:
    """Every server has a logo: /api/logo/dir/<id> always answers with an HD picture (a drawn tile when no real one)."""
    return f"/api/logo/dir/{s[ID]}?v={LOGO_VERSION}"


def logo_sources(eid: str) -> list[tuple[str, str]] | None:
    """Where this server's logo may come from, best first: ('domain', brand site), ('url', listing picture),
    ('gh', GitHub owner); None = no such server."""
    if not _ID.match(eid or ""):
        return None
    s = _by_id().get(eid)
    if s is None:
        return None
    dom, img, owner = (list(s[LOGO]) + ["", "", "", 0])[:3]
    out = []
    if dom:
        out.append(("domain", dom))
    if img and img.startswith("https://"):
        out.append(("url", img))
    if owner:
        out.append(("gh", owner))
    return out


def monogram_of(eid: str) -> tuple[str, str]:
    s = _by_id().get(eid)
    return (s[TITLE] or s[NAME], s[FIELD]) if s else ("MCP", "Other")


NOT_ALLOWED = {
    "whatsapp": "Santosh does not connect unofficial personal-WhatsApp automation (against WhatsApp's terms; numbers get "
                "banned). Use the official WhatsApp Business Platform instead.",
    "scraper": "This Apify actor scrapes other people's websites. Santosh uses official routes only, so it is listed for "
               "reference but not connected. Ask Santosh for an official API or connector that does the same job.",
}


def public(s: list) -> dict[str, Any]:
    mode = connect_mode(s)
    how = {"remote": "Hosted service: add its MCP address (https://...) in Connect > MCP servers, or tell Santosh the address.",
           "local": "Package that runs on a computer: start it on your PC or server with an HTTP transport "
                    "(e.g. via an MCP gateway), then add that https address.",
           "check": "See the project page for how it runs, then add its https MCP address."}[mode]
    if s[SRC] == "apify":
        how = ("Apify actor: needs your Apify API token (Authorization header). Every run spends your Apify credits."
               if s[MCP_URL] else "Apify actor without its own MCP address: see its Apify page.")
    sources = [SOURCE_LABEL.get(x, x) for x in s[SOURCES]] or [SOURCE_LABEL.get(s[SRC], s[SRC])]
    out: dict[str, Any] = {"ref": s[NAME], "id": s[ID], "name": s[TITLE] or s[NAME].split("/")[-1], "field": s[FIELD],
                           "does": s[SHORT] or s[DOES] or "(no description published)", "link": s[LINK],
                           "github": s[REPO] or s[LINK], "source": SOURCE_LABEL.get(s[SRC], s[SRC]), "sources": sources,
                           "official": bool(s[OFFICIAL]), "language": s[LANG],
                           "pricing": ("Apify: pay per use (your credits)" if s[SRC] == "apify" else
                                       "Hosted service (account / API key likely)" if s[PRICE] == "cloud" else
                                       "Free / open source"),
                           "connect": mode, "how_to_connect": how, "logo": logo_path(s)}
    if s[DOES] and s[DOES] != s[SHORT]:
        out["about"] = s[DOES]
    if s[BY]:
        out["by"] = s[BY]
    if s[MCP_URL]:
        out["mcp_url"] = s[MCP_URL]
    if s[HOME]:
        out["website"] = s[HOME]
    if s[VERIFIED]:
        out["verified"] = True
    if s[FEATURED]:
        out["featured"] = True
    if s[TAGS]:
        out["tags"] = s[TAGS]
    for k, i in (("version", VER), ("released", REL), ("licence", LIC)):
        if s[i]:
            out[k] = s[i]
    if s[SRC] == "apify":
        if s[USERS]:
            out["users_per_month"] = s[USERS]
        out["key_header"] = "Authorization"
    elif s[DL]:
        out["downloads_per_month"] = s[DL]
    if install_hint(s):
        out["install"] = install_hint(s)
    b = blocked(s)
    if b:
        out["connect"] = "not_allowed"
        out["how_to_connect"] = NOT_ALLOWED[b]
    if risky(s):
        out["caution"] = ("Can act on money, crypto, code or the computer (or inspects other software). Santosh asks "
                          "before every action; only add it if you trust the publisher and use it on software you own.")
    return out


def search(query: str, limit: int = 6, field: str = "") -> list[dict[str, Any]]:
    words = _words(query)
    fl = field.lower()
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
            title = (s[TITLE] or "").lower()
            if title and title == " ".join(words):
                sc += 6                       # "stripe" -> the server called Stripe first
            sc += (4 if hit_all else 0) + prior
        elif fl:
            sc = prior
        else:
            continue
        scored.append((sc, s))
    scored.sort(key=lambda x: (-x[0], (x[1][TITLE] or x[1][NAME]).lower()))
    return [public(s) for _, s in scored[:max(1, min(limit, 30))]]


@lru_cache
def _by_key() -> dict[str, list]:
    out: dict[str, list] = {}
    for s in servers():
        keys = [s[NAME].lower(), s[LINK].lower().rstrip("/"), s[REPO].lower().rstrip("/"), str(s[N]), s[ID]]
        keys += [a.lower() for a in s[ALIASES]]
        for k in keys:
            if k and k not in out:
                out[k] = s
    return out


@lru_cache
def _by_id() -> dict[str, list]:
    return {s[ID]: s for s in servers()}


def get(ref: str) -> dict[str, Any] | None:
    """Raw entry as a dict with the keys custom_mcp expects (r = ref, d = description, f = field, c = caution, l = link)."""
    s = _by_key().get((ref or "").strip().lower().rstrip("/"))
    if s is None:
        return None
    return {"n": s[N], "r": s[NAME], "d": s[SHORT] or s[DOES], "f": s[FIELD], "c": risky(s), "l": s[REPO] or s[LINK],
            "o": s[OFFICIAL], "blocked": blocked(s), "id": s[ID], "t": s[TITLE] or s[NAME].split("/")[-1],
            "u": s[MCP_URL], "src": s[SRC]}


def stats() -> dict[str, Any]:
    fields: dict[str, int] = {}
    sources: dict[str, int] = {}
    remote = 0
    for s in servers():
        fields[s[FIELD]] = fields.get(s[FIELD], 0) + 1
        for x in s[SOURCES] or [s[SRC]]:
            lab = SOURCE_LABEL.get(x, x)
            sources[lab] = sources.get(lab, 0) + 1
        remote += connect_mode(s) == "remote"
    return {"total": len(servers()), "hosted": remote, "fields": dict(sorted(fields.items(), key=lambda x: -x[1])),
            "categories": categories(), "sources": sources, "source": _data()["source"]}
