"""v0.999.254 MAKE PARITY - THE GRID (Make Grid's idea, own code): one map of all her routes and what they touch.

Nodes: every route (on / off, how it starts, its last run), every data store, every app a route uses, the webhook
and form / chat addresses. Links: a route runs another (sub-route step), a route's error route, routes started
when any route fails, a route that reads or writes a data store, a route that uses an app. Read-only - it draws
what the routes already say; nothing here changes a route.
"""
from __future__ import annotations

from typing import Any


def _walk(steps: list) -> list[dict]:
    out: list[dict] = []
    for s in steps or []:
        if not isinstance(s, dict):
            continue
        out.append(s)
        for k in ("then", "else", "fallback"):
            out.extend(_walk(s.get(k) or []))
        if s.get("type") == "loop":
            out.extend(_walk(s.get("body") or []))
        for rt in s.get("routes") or []:
            if isinstance(rt, dict):
                out.extend(_walk(rt.get("steps") or []))
        oe = s.get("on_error")
        if isinstance(oe, dict):
            out.extend(_walk(oe.get("steps") or []))
    return out


def build(tenant: str) -> dict[str, Any]:
    from ..agent import dhara_tools as D
    from . import api as A
    from . import store as DS
    con = D._con(tenant)
    try:
        wfs = [D._wf_row(r) for r in con.execute("SELECT * FROM workflows ORDER BY name").fetchall()]
    finally:
        con.close()
    by_name = {w["name"]: w for w in wfs}
    nodes: list[dict] = []
    links: list[dict] = []
    seen: set[str] = set()

    def node(nid: str, **kw) -> None:
        if nid not in seen:
            seen.add(nid)
            nodes.append({"id": nid, **kw})

    error_starts = [w for w in wfs if w.get("trigger_kind") == "error"]
    for w in wfs:
        rid = "route:" + w["name"]
        last = D.latest_run(tenant, w["id"])
        node(rid, kind="route", name=w["name"], route_id=w["id"], enabled=bool(w.get("enabled")),
             trigger=w.get("trigger_kind") or "manual", folder=(w.get("settings") or {}).get("folder") or "",
             last=(last or {}).get("status") if last else None)
        if w.get("trigger_kind") in ("webhook", "form", "chat", "tool"):
            hid = f"door:{w['name']}"
            node(hid, kind="door", name={"webhook": "Webhook", "form": "Form page", "chat": "Chat page",
                                        "tool": "MCP tool"}[w["trigger_kind"]], of=w["name"])
            links.append({"from": hid, "to": rid, "kind": "starts"})
        er = (w.get("settings") or {}).get("error_route")
        if er:
            links.append({"from": rid, "to": "route:" + er, "kind": "on_error", "missing": er not in by_name})
        for e in error_starts:               # a route that starts when this one (or any route) fails
            watched = (e.get("trigger_spec") or {}).get("routes") or []
            if e["name"] != w["name"] and (not watched or w["name"] in watched):
                links.append({"from": rid, "to": "route:" + e["name"], "kind": "on_error_any"})
        for s in _walk(w.get("steps") or []):
            t = s.get("type")
            if t == "subroute":
                to = str(s.get("route") or "")
                links.append({"from": rid, "to": "route:" + to, "kind": "runs", "missing": to not in by_name})
            elif t == "store":
                sid = "store:" + str(s.get("store") or "")
                node(sid, kind="store", name=str(s.get("store") or ""))
                links.append({"from": rid, "to": sid, "kind": "writes" if s.get("op") in ("add", "update", "delete",
                                                                                       "delete_all", "increment") else "reads"})
            elif t == "tool":
                a = A.app_of(s)
                if a.get("kind") == "app":
                    aid = "app:" + a["slug"]
                    node(aid, kind="app", name=a["slug"])
                    links.append({"from": rid, "to": aid, "kind": "uses"})
            elif t == "http":
                try:
                    from urllib.parse import urlsplit
                    host = (urlsplit(str(s.get("url") or "")).hostname or "")
                except Exception:   # noqa: BLE001
                    host = ""
                if host and "{{" not in host:
                    hid = "web:" + host
                    node(hid, kind="web", name=host)
                    links.append({"from": rid, "to": hid, "kind": "calls"})
    for st in DS.stores(tenant):
        node("store:" + st["name"], kind="store", name=st["name"], records=st["records"])
    for ln in links:                       # a link to a route that does not exist still shows, marked missing
        if ln["to"].startswith("route:") and ln["to"] not in seen:
            node(ln["to"], kind="route", name=ln["to"][6:], missing=True)
    uniq, keyset = [], set()
    for ln in links:
        k = (ln["from"], ln["to"], ln["kind"])
        if k not in keyset:
            keyset.add(k)
            uniq.append(ln)
    return {"nodes": nodes, "links": uniq,
            "counts": {k: sum(1 for n in nodes if n["kind"] == k) for k in ("route", "store", "app", "web", "door")}}
