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
import re
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
            "oauth_partner": f"{c['name']} only allows approved apps; Hoola's partner access is pending."}.get(c["auth"], "") + (
        " GitHub: a fine-grained personal access token (github.com > Settings > Developer settings > Fine-grained tokens; only "
        "the repos you choose; Contents / Issues / Pull requests / Actions / Metadata). Or one tap with the token you already "
        "gave Developer Sahayak." if c["id"] == "github" else "") + (
        " Supabase: one tap and sign in with your Supabase account (or a personal access token sbp_... from "
        "supabase.com/dashboard/account/tokens). Best: pick one project (project ref) and keep read-only on; writes "
        "(migrations, SQL changes, Edge Function deploys) always wait for your tap." if c["id"] == "supabase" else "") + (
        " " + ZOHO_HOW if c["id"] == "zoho-mcp" else "") + (
        " 21st.dev Magic: sign in at 21st.dev/mcp, make an API key there (old Magic keys no longer work) and paste it here. "
        "Hoola can then make premium UI components from a few words, find design inspiration and brand logos (SVG). It only "
        "returns code; it never changes your site by itself. Uses your 21st.dev credits." if c["id"] == "21st-magic" else "")


ZOHO_HOW = ("Zoho (India): 1) open mcp.zoho.in and sign in with your Zoho account (zoho.com accounts: mcp.zoho.com). "
            "2) Create MCP Server, give it a name. 3) Tools > Add Tools: tick only what your work needs (Books, CRM, Mail, "
            "Desk...); keep it under about 60 tools, Hoola's starter list shows the useful ones. 4) Connect tab: copy the "
            "server address and paste it here. It carries a private key: Hoola keeps it locked and never shows it; never "
            "paste it in chat. 5) The first time, sign in to Zoho once. Reads run straight; creating, sending, deleting and "
            "payments always wait for your tap. Leaked? Regenerate API Key in the Connect tab and paste the new address.")


def zoho_url(c: dict[str, Any], url: str) -> str:
    """v0.288 her Zoho MCP server address: https on Zoho's MCP domains only (the console page itself is not the server)."""
    from urllib.parse import urlparse
    url = (url or "").strip()
    u = urlparse(url)
    host = (u.hostname or "").lower()
    hosts = (c.get("options") or {}).get("hosts") or []
    if host.startswith("mcp.zoho."):
        raise ValueError("Yeh Zoho MCP ka console page hai. Wahan apna server kholo > Connect tab > server address copy karke "
                          "yahan daalo (…zohomcp.in/… jaisa).")
    if u.scheme != "https" or not any(host == h or host.endswith("." + h) for h in hosts):
        raise ValueError("Zoho MCP address …zohomcp.in (ya .com / .eu) par hota hai: mcp.zoho.in > apna server > Connect "
                          "tab se copy karo.")
    return url


SUPA_REF = re.compile(r"^[a-z]{20}$")


def supabase_url(c: dict[str, Any], readonly: bool | None = None, features: list[str] | None = None,
                 project: str = "") -> str:
    """v0.145 Supabase's documented query parameters on its remote MCP URL: read_only=true (a read-only Postgres user),
    project_ref=<ref> (one project, account tools off), features=<groups> (only those tool groups). skip_elicitations is
    never set, so Supabase's own confirmations stay on too."""
    from urllib.parse import urlencode
    opt = c.get("options") or {}
    allowed = opt.get("features") or []
    pick = [f for f in (features or []) if f in allowed] or list(opt.get("default_features") or [])
    project = (project or "").strip().lower()
    if project and not SUPA_REF.match(project):
        raise ValueError("Supabase project ref = 20 small letters (Project Settings > General > Project ID)")
    if project:
        pick = [f for f in pick if f != "account"]   # Supabase turns account tools off in project mode anyway
    q: dict[str, str] = {}
    if project:
        q["project_ref"] = project
    if readonly is None or readonly:
        q["read_only"] = "true"
    q["features"] = ",".join(dict.fromkeys(pick))
    return c["url"].split("?")[0] + "?" + urlencode(q, safe=",")


def supabase_settings(url: str) -> dict[str, Any]:
    from urllib.parse import parse_qs, urlparse
    q = parse_qs(urlparse(url or "").query)
    return {"project": (q.get("project_ref") or [""])[0], "readonly": (q.get("read_only") or [""])[0] == "true",
            "features": [f for f in (q.get("features") or [""])[0].split(",") if f]}


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
