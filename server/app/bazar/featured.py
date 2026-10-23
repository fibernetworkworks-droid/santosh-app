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
            "oauth_partner": f"{c['name']} only allows approved apps; Santosh's partner access is pending."}.get(c["auth"], "") + (
        " GitHub: a fine-grained personal access token (github.com > Settings > Developer settings > Fine-grained tokens; only "
        "the repos you choose; Contents / Issues / Pull requests / Actions / Metadata). Or one tap with the token you already "
        "gave Developer Sahayak." if c["id"] == "github" else "")


def headers_of(c: dict[str, Any], readonly: bool | None = None, toolsets: list[str] | None = None) -> dict[str, str]:
    """v0.143 request headers the server documents for safety / scope (GitHub: X-MCP-Lockdown, X-MCP-Toolsets,
    X-MCP-Readonly; see docs/remote-server.md)."""
    out = dict(c.get("headers") or {})
    opt = c.get("options") or {}
    if opt.get("kind") == "github":
        allowed = opt.get("toolsets") or []
        pick = [t for t in (toolsets or []) if t in allowed] or list(opt.get("default_toolsets") or [])
        if "context" in allowed and "context" not in pick:
            pick.insert(0, "context")
        out["X-MCP-Toolsets"] = ",".join(dict.fromkeys(pick))
        if readonly:
            out["X-MCP-Readonly"] = "true"
    return out


def public(c: dict[str, Any], status: str = "") -> dict[str, Any]:
    out = {"id": c["id"], "name": c["name"], "category": c["category"], "does": c.get("does", ""), "auth": c["auth"],
           "one_tap": c["auth"] in ONE_TAP, "how_to_connect": how(c), "docs": c.get("source", "")}
    if c.get("url_hint"):
        out["url_hint"] = c["url_hint"]
    if c.get("india"):
        out["india"] = True
    if c.get("native"):
        out["native"] = c["native"]
    if c.get("options"):
        out["options"] = {k: v for k, v in c["options"].items() if k != "reuse"}
    if c.get("caution"):
        out["caution"] = True
    if status:
        out["status"] = status
    from .logos import featured_logo
    out["logo"] = featured_logo(c["id"])
    return out
