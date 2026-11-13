"""v0.877 HOOLA AGENT API - what an outside company may call.

An ALLOWLIST, never "every tool": a tool is here only if it reads or computes and does not send, pay, delete, share,
use the owner's personal accounts, or move a PC. Adding a row = a decision (and a test); the price is a default the owner can
override with the `hoola_api_prices` setting ({"tool": micro_inr}).

Price unit: micro-INR (1 INR = 1,000,000). The numbers below are PLACEHOLDER defaults, not measured costs.
"""
from __future__ import annotations

import json
from typing import Any

INR = 1_000_000

# name -> (group, title, default price in micro-INR)
CATALOG: dict[str, tuple[str, str, int]] = {
    "api_box":     ("india-data", "Free public APIs in one call (GSTIN, mandi prices, news, share prices, court data...)", 1 * INR),
    "mospi":       ("india-data", "Official Indian statistics (CPI, GDP, IIP, PLFS...) from MoSPI", 500_000),
    "duniya":      ("web", "Keyless public web: Wikipedia, weather, currency, dictionary, arXiv, Hacker News", 250_000),
    "reach":       ("web", "Read or search the web through ordered backends with one answer shape", 1 * INR),
    "scrape_page": ("web", "Read one web page as clean markdown / text (robots + SSRF guarded)", 1 * INR),
    "pylab":       ("compute", "Run a short Python calculation in a locked sandbox (no network)", 500_000),
}


def prices() -> dict[str, int]:
    """Default prices with the owner's overrides applied (a bad or negative override is ignored)."""
    out = {n: v[2] for n, v in CATALOG.items()}
    try:
        from ..config import get_settings
        raw = getattr(get_settings(), "hoola_api_prices", "") or ""
        over = json.loads(raw) if isinstance(raw, str) and raw.strip() else (raw or {})
        for n, v in (over or {}).items():
            if n in out and isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                out[n] = v
    except Exception:       # noqa: BLE001 - a broken override must never take the API down
        pass
    return out


def schemas() -> dict[str, dict[str, Any]]:
    """name -> {description, input_schema} for the catalogue tools that are really registered."""
    from ..agent import tools as T
    have = {t["name"]: t for t in T.TOOLS if isinstance(t, dict) and t.get("name") in CATALOG}
    return {n: {"description": have[n].get("description", ""), "input_schema": have[n].get("input_schema") or
                {"type": "object", "properties": {}}} for n in CATALOG if n in have}


def listing() -> list[dict[str, Any]]:
    """The public tool list: only tools that exist, with their schema and INR price."""
    pr, sc = prices(), schemas()
    rows = []
    for n, s in sc.items():
        group, title, _d = CATALOG[n]
        rows.append({"name": n, "group": group, "title": title, "description": s["description"][:600],
                     "input_schema": s["input_schema"], "price_micro_inr": pr[n], "price_inr": pr[n] / INR})
    return rows
