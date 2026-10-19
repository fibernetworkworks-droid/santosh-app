"""Santosh Agent Army: a catalogue of 36,336 open-source AI agents worldwide (37 fields), so Santosh can find the
right agent, framework or tool for any job, explain it, compare options and say how it can be used.

A catalogue, not code Santosh runs: open-source agents run code, browse, send email and can spend money, so they are
never executed on Santosh's server. What Santosh does with them:
  * search / compare / recommend (Tier A-B first: real usage signals) and explain in plain words
  * agents that are MCP servers -> connect through Connect > MCP servers (with the usual confirm cards)
  * ready-made agent apps -> self-host on your PC/server (Santosh guides), or Newtika integrates them
  * frameworks / SDKs -> for developers building agents
Licence traps (modified Apache, Sustainable Use, AGPL, FSL...) and risky kinds are flagged. Rebuild with
tools/build_agent_directory.py.
"""
from __future__ import annotations

import gzip
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

FILE = Path(__file__).parent / "agents_directory.json.gz"
(N, NAME, LINK, FIELD, ALSO, DOES, KIND, FOUND, LANG, STARS, NPM, TREND, REL, LIC, LISTS, PKGS, SCORE, TIER) = range(18)
TIER_LABEL = {"A": "A · proven", "B": "B · established", "C": "C · early / niche", "D": "D · unproven"}
STOP = {"the", "and", "for", "with", "from", "agent", "agents", "ai", "an", "a", "of", "to", "in", "on", "use", "using",
        "your", "kar", "karo", "ka", "ki", "ke", "hai", "mujhe", "chahiye", "wala", "wali", "ko", "se", "me", "mein",
        "aur", "koi", "do", "best", "open", "source", "tool", "tools"}

_RISK = re.compile(r"exploit|pentest|penetration|malware|red[- ]?team|\bc2\b|phish|crack|jailbreak|trading bot|"
                   r"\btrad(e|ing)\b|crypto|wallet|defi|solana|ethereum|polymarket|betting|shell|execute (any|arbitrary)|"
                   r"computer[- ]use|remote control|keylog|spy", re.I)
_RISK_FIELDS = {"Cybersecurity", "Finance, trading & investing", "Browser, web & computer-use"}
_WA = re.compile(r"whats\s?app", re.I)
_WA_OK = re.compile(r"business (platform|api)|cloud api|whatsapp business api|meta (graph|cloud)", re.I)
# well-known licence traps for commercial / multi-tenant use (see the sheet's notes)
_LIC_TRAPS = [
    (re.compile(r"^dify\s|langgenius/dify\b", re.I), "Dify: modified Apache licence (limits multi-tenant SaaS and removing its branding)"),
    (re.compile(r"^n8n\s|n8n-io/n8n\b", re.I), "n8n: Sustainable Use Licence (not free for commercial hosting for others)"),
    (re.compile(r"^open[- ]?webui\s|open-webui/open-webui\b", re.I), "Open WebUI: branding clause in its licence"),
]
_LIC_WORDS = re.compile(r"\bAGPL|\bSSPL|\bBUSL|Business Source|\bFSL\b|Functional Source|Sustainable Use|Commons Clause|"
                        r"Elastic License|non-?commercial|\bCC[- ]BY[- ]NC", re.I)


@lru_cache
def _data() -> dict[str, Any]:
    with gzip.open(FILE, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def agents() -> list[list]:
    return _data()["agents"]


def _num(v) -> float:
    return float(v) if isinstance(v, (int, float)) else 0.0


@lru_cache
def _index() -> list[tuple[list, str, str, float]]:
    out = []
    for a in agents():
        prior = _num(a[SCORE]) / 12 + {"A": 4, "B": 2, "C": 0.5}.get(a[TIER], 0) + min(2.0, _num(a[LISTS])) \
            + min(2.0, math.log10(_num(a[NPM]) + 1) / 3) + min(2.0, math.log10(_num(a[STARS]) + 1) / 2.5)
        out.append((a, a[NAME].lower(), f"{a[FIELD]} {a[ALSO]} {a[DOES]} {a[PKGS]} {a[LINK]}".lower(), prior))
    return out


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9.+#-]*", (text or "").lower()) if len(w) > 1 and w not in STOP]


def is_mcp(a: list) -> bool:
    return bool(re.search(r"\bmcp\b|model context protocol|-mcp\b|mcp-", f"{a[NAME]} {a[DOES]} {a[PKGS]}", re.I))


def risky(a: list) -> bool:
    return a[FIELD] in _RISK_FIELDS or bool(_RISK.search(f"{a[NAME]} {a[DOES]}"))


def blocked(a: list) -> bool:
    hay = f"{a[NAME]} {a[DOES]}"
    return bool(_WA.search(hay)) and not _WA_OK.search(hay)


def licence_note(a: list) -> str:
    hay = f"{a[NAME]} {a[LINK]}"
    for rx, note in _LIC_TRAPS:
        if rx.search(hay):
            return note
    lic = str(a[LIC] or "")
    if _LIC_WORDS.search(lic):
        return f"Licence '{lic}' restricts commercial or hosted use; read it before using for clients"
    if not lic:
        return "Licence not listed here: check the repo's LICENSE before commercial or multi-tenant use"
    return ""


def how_to_use(a: list) -> str:
    if blocked(a):
        return ("Not used by Santosh: unofficial personal-WhatsApp automation breaks WhatsApp's terms (numbers get "
                "banned). Use the official WhatsApp Business Platform instead.")
    if is_mcp(a):
        return ("Has an MCP server: run it (or use its hosted address) and add the https MCP address in Santosh > "
                "Connect > MCP servers; every non-read action then needs your tap.")
    if a[KIND] == "Framework / SDK":
        return "A developer toolkit for building agents (not a ready-made agent). Good base for custom work by your tech team / Newtika."
    if a[KIND] == "Plugin / tool / connector":
        return "A plugin/tool that other agents use. Useful when building on that agent platform."
    return ("A ready-made agent app: self-host it on your own PC/server (sandboxed, least-privilege keys), or ask "
            "Newtika to integrate it into Santosh.")


def public(a: list, full: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"ref": a[N], "name": a[NAME], "link": a[LINK], "field": a[FIELD], "does": a[DOES] or "(no description)",
                           "kind": a[KIND], "tier": TIER_LABEL.get(a[TIER], a[TIER]), "score": a[SCORE],
                           "language": a[LANG], "how_to_use": how_to_use(a)}
    if a[ALSO]:
        out["also_fits"] = a[ALSO]
    for k, i in (("github_stars", STARS), ("npm_downloads_month", NPM), ("days_trending", TREND), ("last_release", REL),
                 ("licence", LIC), ("in_curated_lists", LISTS)):
        if a[i] not in ("", None, 0):
            out[k] = a[i]
    if full:
        out["found_in"] = a[FOUND]
        if a[PKGS]:
            out["packages"] = a[PKGS]
    note = licence_note(a)
    if note:
        out["licence_note"] = note
    if risky(a):
        out["caution"] = ("Can run code, browse, trade or touch security/money. Run only in a sandbox with "
                          "least-privilege keys; never give it production credentials.")
    if blocked(a):
        out["blocked"] = True
    return out


def search(query: str = "", field: str = "", kind: str = "", tier: str = "", limit: int = 8) -> list[dict[str, Any]]:
    words = _words(query)
    fl, kl = field.strip().lower(), kind.strip().lower()
    tiers = {t.strip().upper()[:1] for t in tier.replace("+", ",").split(",") if t.strip()}
    scored = []
    for a, name, hay, prior in _index():
        if fl and fl not in a[FIELD].lower() and fl not in str(a[ALSO]).lower():
            continue
        if kl and kl not in a[KIND].lower():
            continue
        if tiers and a[TIER] not in tiers:
            continue
        if words:
            sc, hit_all = 0.0, True
            for w in words:
                inn, inh = w in name, w in hay
                sc += (6 if inn else 0) + (2 if inh else 0)
                hit_all &= inn or inh
            if not sc:
                continue
            sc += (5 if hit_all else 0) + prior
        elif fl or kl or tiers:
            sc = prior
        else:
            continue
        scored.append((sc, a))
    scored.sort(key=lambda x: (-x[0], str(x[1][NAME]).lower()))
    return [public(a) for _, a in scored[:max(1, min(int(limit or 8), 40))]]


@lru_cache
def _by_key() -> dict[str, list]:
    out: dict[str, list] = {}
    for a in agents():
        for k in (str(a[N]), str(a[NAME]).lower(), str(a[LINK]).lower().rstrip("/")):
            if k and k not in out:
                out[k] = a
    return out


def get(ref: str | int) -> dict[str, Any] | None:
    a = _by_key().get(str(ref).strip().lower().rstrip("/"))
    return public(a, full=True) if a else None


def fields() -> list[dict[str, Any]]:
    return _data()["fields"]


def stats() -> dict[str, Any]:
    tiers: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for a in agents():
        tiers[TIER_LABEL.get(a[TIER], a[TIER])] = tiers.get(TIER_LABEL.get(a[TIER], a[TIER]), 0) + 1
        kinds[a[KIND]] = kinds.get(a[KIND], 0) + 1
    notes = _data()["notes"]
    return {"total": len(agents()), "tiers": tiers, "kinds": kinds, "curated": _data()["curated"],
            "fields": fields(), "how_to_read": notes.get("HOW TO READ", ""), "safety": notes.get("Safety", ""),
            "source": _data()["source"]}
