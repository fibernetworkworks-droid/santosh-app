"""MCP directory: 3,184 community MCP servers (from the user's sheet, sourced from awesome-mcp-servers).

This is a catalogue, not code Santosh runs. A server becomes usable when the user connects it:
remote ("Cloud") servers by their HTTPS MCP address; "Local" servers need a computer to run on
(the user's own PC/host, then its address is added the same way).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

FILE = Path(__file__).parent / "mcp_directory.json"
STOP = {"the", "and", "for", "with", "from", "mcp", "server", "servers", "tool", "tools", "use", "using", "your", "kar",
        "karo", "ka", "ki", "ke", "hai", "mujhe", "chahiye", "wala", "wali", "ko", "se", "me", "mein", "aur"}


@lru_cache
def _data() -> dict[str, Any]:
    return json.loads(FILE.read_text())


def servers() -> list[dict[str, Any]]:
    return _data()["servers"]


@lru_cache
def _index() -> list[tuple[dict[str, Any], str, str]]:
    return [(s, s["r"].lower(), f"{s['f']} {s['d']}".lower()) for s in servers()]


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9][a-z0-9.+-]*", text.lower()) if len(w) > 1 and w not in STOP]


def connect_mode(s: dict[str, Any]) -> str:
    run = s.get("run", "")
    if "Cloud" in run:
        return "remote"
    if "Local" in run or "Embedded" in run:
        return "local"
    return "unknown"


def public(s: dict[str, Any]) -> dict[str, Any]:
    mode = connect_mode(s)
    how = {"remote": "Hosted service: add its MCP address (https://...) in Connect > MCP servers, or tell Santosh the address.",
           "local": "Runs on a computer: start it on your PC or server with an HTTP/SSE transport, then add that https address.",
           "unknown": "Check the GitHub page for how it runs, then add its https MCP address."}[mode]
    out = {"ref": s["r"], "name": s["r"].split("/")[-1], "field": s["f"], "does": s["d"], "github": s["l"],
           "official": s["o"], "runs": s["run"] or "not stated", "language": s["lang"], "connect": mode, "how_to_connect": how}
    if s["c"]:
        out["caution"] = ("Can act on money, crypto, code or the computer. Santosh asks before every action; "
                          "only add it if you trust the publisher.")
    return out


def search(query: str, limit: int = 6, field: str = "") -> list[dict[str, Any]]:
    words = _words(query)
    fl = field.lower()
    scored = []
    for s, repo, hay in _index():
        if fl and fl not in s["f"].lower():
            continue
        if not words:
            continue
        sc = 0
        for w in words:
            if w in repo:
                sc += 4
            if re.search(r"(?<![a-z0-9])" + re.escape(w), hay):
                sc += 2
            elif w in hay:
                sc += 1
        if not sc:
            continue
        hit_all = all(w in repo or w in hay for w in words)
        sc += (3 if hit_all else 0) + (2 if s["o"] else 0) + (1 if "Cloud" in s["run"] else 0)
        scored.append((sc, s))
    scored.sort(key=lambda x: (-x[0], x[1]["r"].lower()))
    return [public(s) for _, s in scored[:max(1, min(limit, 20))]]


def get(ref: str) -> dict[str, Any] | None:
    ref = (ref or "").strip().lower()
    for s in servers():
        if s["r"].lower() == ref or str(s["n"]) == ref or s["l"].lower().rstrip("/") == ref.rstrip("/"):
            return s
    return None


def stats() -> dict[str, Any]:
    fields: dict[str, int] = {}
    remote = 0
    for s in servers():
        fields[s["f"]] = fields.get(s["f"], 0) + 1
        remote += "Cloud" in s["run"]
    return {"total": len(servers()), "remote": remote, "fields": dict(sorted(fields.items(), key=lambda x: -x[1])),
            "source": _data()["source"]}
