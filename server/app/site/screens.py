"""v0.989 B1 LIVE SCREENS (owner: "GO B1 B2"; research docs/research/lovable/03_backend_vs_hoola.md gap 1).

A portal's designed screens (dashboard, table, form, detail, board, calendar, approvals, sign-in, settings) were static
HTML with invented sample rows and dead buttons; only the generic /account/ shell showed real data. Now every screen is
TIED to one of the site's real lists:

- the section writer is told the real lists (key, label, fields, who reads) and marks the screen with `data-list`,
  `data-fields`, the element holding the sample rows `data-hoola-live`, KPI tiles `data-hoola-stat`, the "Sample data"
  chip `data-sample-chip` and its add button `data-hoola-add`;
- `bind()` (here, at page build) checks those against the real schema: an unknown list is matched by key / label or the
  only list there is, unknown fields are dropped, a sign-in screen always gets Hoola's own sign-in box; a tied screen
  loses `data-sample` (so it no longer blocks going live) and gets `data-bound`;
- the page script (`assets/hoola-app.js` `screens()`) fills a tied screen from the real rows the visitor may see, under
  the same server-side rules as every call; the sample rows stay only in the Studio preview while a list is empty.
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

ALWAYS = ("screen_signin", "screen_settings", "screen_approvals")      # tied without a list
SKIP_TYPES = ("signature", "photos", "video", "audio", "richtext", "file", "photo", "location", "scan")


def _colls(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return [c for c in (schema or {}).get("collections") or [] if not str(c.get("key", "")).startswith("_")]


def _norm(x: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(x or "").lower()).rstrip("s")


def lists_line(schema: dict[str, Any]) -> str:
    """The real lists, for the section writer of an app screen."""
    out = []
    for c in _colls(schema)[:16]:
        fs = ", ".join(f'{f["key"]}:{f.get("type", "text")}' + (f'[{"/".join(map(str, (f.get("options") or [])[:6]))}]'
                                                                if f.get("type") == "choice" else "")
                       for f in (c.get("fields") or [])[:14] if not f.get("hidden"))
        r = c.get("rules") or {}
        out.append(f'{c["key"]} ("{c.get("label") or c["key"]}"; read {r.get("read")}, create {r.get("create")}): {fs}')
    return "\n".join(out)


def _pick(key: str, el, colls: list[dict[str, Any]]) -> dict[str, Any] | None:
    by = {c["key"]: c for c in colls}
    if key in by:
        return by[key]
    n = _norm(key)
    for c in colls:
        if n and (n == _norm(c["key"]) or n == _norm(c.get("label"))):
            return c
    if len(colls) == 1:
        return colls[0]
    text = _norm(el.get_text(" ", strip=True)[:400])
    hits = [c for c in colls if _norm(c.get("label")) and _norm(c.get("label")) in text]
    return hits[0] if len(hits) == 1 else None


def _fields(want: str, c: dict[str, Any]) -> list[str]:
    have = {f["key"]: f for f in c.get("fields") or [] if not f.get("hidden")}
    keys = [k.strip() for k in str(want or "").split(",") if k.strip() in have]
    if not keys:
        keys = [k for k, f in have.items() if f.get("type") not in SKIP_TYPES][:4]
    return keys[:8]


def bind(html: str, schema: dict[str, Any]) -> tuple[str, list[str]]:
    """Tie every app screen in a section to the site's real lists (see the module note). Returns (html, problems)."""
    if "data-hoola-screen" not in html:
        return html, []
    colls = _colls(schema)
    soup = BeautifulSoup(html, "html.parser")
    problems: list[str] = []
    for el in soup.select("[data-hoola-screen]"):
        typ = str(el.get("data-hoola-screen") or "")
        if typ == "screen_signin" and not el.select_one('[data-hoola-app="login"]'):
            box = el.select_one("[data-hoola-live]") or el
            if box is not el:
                box.clear()
            box.append(soup.new_tag("div", attrs={"data-hoola-app": "login"}))
        c = _pick(str(el.get("data-list") or ""), el, colls) if colls else None
        if c is None and typ not in ALWAYS:
            el.attrs.pop("data-list", None)
            problems.append(f"{typ.replace('screen_', '')} screen is not tied to a list yet (still sample data)")
            continue
        if c is not None:
            el["data-list"] = c["key"]
            el["data-fields"] = ",".join(_fields(str(el.get("data-fields") or ""), c))
        for st in el.select("[data-hoola-stat]"):
            sc = _pick(str(st.get("data-list") or ""), st, colls) if st.get("data-list") else c
            if sc is None:
                st.attrs.pop("data-hoola-stat", None)
                continue
            st["data-list"] = sc["key"]
            agg = str(st.get("data-hoola-stat") or "count")
            if agg.startswith("sum:") and agg[4:] not in {f["key"] for f in sc.get("fields") or []}:
                st["data-hoola-stat"] = "count"
        el.attrs.pop("data-sample", None)
        el["data-bound"] = ""
    return str(soup), problems
