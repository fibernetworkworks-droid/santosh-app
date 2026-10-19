"""Featured connectors: well-known apps that publish an official remote MCP server (the same ones found in Claude's
connector directory). One tap in the app connects them to Santosh.

auth:
  oauth_dcr      sign in with the app (Santosh registers itself automatically) -> one tap
  api_key        the user pastes an API key in the app (never in chat)
  per_user_url   the app gives each user a private MCP address (e.g. Zapier); the user pastes it
  oauth_partner  the app only lets pre-approved clients sign in; needs a Santosh partner app with that vendor
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

FILE = Path(__file__).parent / "featured_mcp.json"
ONE_TAP = {"oauth_dcr", "none"}


@lru_cache
def items() -> list[dict[str, Any]]:
    if not FILE.exists():
        return []
    return json.loads(FILE.read_text())["connectors"]


def get(fid: str) -> dict[str, Any] | None:
    fid = (fid or "").strip().lower()
    for c in items():
        if c["id"] == fid or c["name"].lower() == fid:
            return c
    return None


def search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    words = [w for w in query.lower().replace("/", " ").split() if len(w) > 2]
    out = []
    for c in items():
        hay = f"{c['name']} {c['category']} {c.get('does', '')} {' '.join(c.get('keywords', []))}".lower()
        sc = sum(3 if w in c["name"].lower() else 1 for w in words if w in hay)
        if sc:
            out.append((sc, c))
    out.sort(key=lambda x: -x[0])
    return [public(c) for _, c in out[:limit]]


def how(c: dict[str, Any]) -> str:
    return {"oauth_dcr": "One tap: Connect, then sign in with your account.",
            "none": "One tap: Connect.",
            "api_key": f"Connect, then paste your {c['name']} API key in the app (never in chat).",
            "per_user_url": f"Copy your personal MCP address from {c['name']} and paste it in the app.",
            "oauth_partner": f"{c['name']} only allows approved apps; Santosh's partner access is pending."}.get(c["auth"], "")


def public(c: dict[str, Any], status: str = "") -> dict[str, Any]:
    out = {"id": c["id"], "name": c["name"], "category": c["category"], "does": c.get("does", ""), "auth": c["auth"],
           "one_tap": c["auth"] in ONE_TAP, "how_to_connect": how(c), "docs": c.get("source", "")}
    if c.get("india"):
        out["india"] = True
    if c.get("native"):
        out["native"] = c["native"]
    if status:
        out["status"] = status
    return out
