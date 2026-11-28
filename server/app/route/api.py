"""v0.999.87 HOOLA ROUTE - the console page's API (owner: "GO" on the Hoola Route panel canvas).

One engine: every route IS a DHARA workflow (agent/dhara_tools.py); this module only reads it for the page and
relays HER taps (switch on/off, run once, approve, stop, retry). Building or changing a route stays a chat
job - the page hands her words to Hoola in a real conversation, Hoola calls dhara_save, and the page shows it.

Mounted with `app.include_router(route_api.make_router(require_key, current_tenant))`, prefix /api/route.
Everything is tenant-scoped by the same sign-in as the rest of the console. Nothing here moves money or sends a
message: a tap on Approve is her yes, exactly like typing it in the chat.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

# tool-name prefix -> the app whose logo the page shows (/api/logo/cmp/<slug>, the Connectors page's logos)
_APP_OF = (
    ("gmail", "gmail"), ("email", "gmail"), ("mail_", "gmail"), ("sheets", "googlesheets"), ("sheet_", "googlesheets"),
    ("gsheet", "googlesheets"), ("drive", "googledrive"), ("gdrive", "googledrive"), ("calendar", "googlecalendar"),
    ("gcal", "googlecalendar"), ("docs_", "googledocs"), ("whatsapp", "whatsapp"), ("wa_", "whatsapp"),
    ("campaign", "whatsapp"), ("slack", "slack"), ("notion", "notion"), ("hubspot", "hubspot"),
    ("quickbooks", "quickbooks"), ("xero", "xero"), ("stripe", "stripe"), ("shopify", "shopify"),
    ("instagram", "instagram"), ("youtube", "youtube"), ("telegram", "telegram"), ("trello", "trello"),
    ("airtable", "airtable"), ("github", "github"), ("zoom", "zoom"), ("salesforce", "salesforce"),
)
_KIND_ICON = {"http": "http", "code": "code", "wait": "wait", "notify": "notify", "approval": "approval",
              "router": "router", "filter": "filter", "condition": "router", "loop": "loop", "set": "set"}


def app_of(step: dict) -> dict[str, str]:
    """What the page draws for one step: {kind, slug, label}. A tool step maps to its app when the tool name says
    which one; a composio step carries its own app slug; anything else is a Hoola tool (the Orbit mark)."""
    typ = str(step.get("type") or "")
    if typ != "tool":
        return {"kind": _KIND_ICON.get(typ, typ), "slug": "", "label": typ}
    name = str(step.get("name") or "").lower()
    args = step.get("args") or {}
    if name.startswith("composio") and isinstance(args, dict):
        app = str(args.get("app") or args.get("toolkit") or "").lower().strip()
        if app:
            return {"kind": "app", "slug": app[:40], "label": app}
    for pre, slug in _APP_OF:
        if name.startswith(pre) or f"_{pre}" in name:
            return {"kind": "app", "slug": slug, "label": slug}
    return {"kind": "hoola", "slug": "", "label": name}


def _walk(steps: list) -> list[dict]:
    out: list[dict] = []
    for s in steps or []:
        if not isinstance(s, dict):
            continue
        out.append(s)
        for k in ("then", "else", "body", "fallback"):
            if k != "body" or s.get("type") == "loop":      # a web request's body is data, not steps
                out.extend(_walk(s.get(k) or []))
        for rt in s.get("routes") or []:
            if isinstance(rt, dict):
                out.extend(_walk(rt.get("steps") or []))
        oe = s.get("on_error")                       # v0.999.258: an error handler's own steps
        if isinstance(oe, dict) and isinstance(oe.get("steps"), list):
            out.extend(_walk(oe["steps"]))
    return out


def apps_of(steps: list) -> list[dict]:
    seen, out = set(), []
    for s in _walk(steps):
        a = app_of(s)
        if a["kind"] not in ("app", "hoola", "http"):
            continue
        key = a["slug"] or a["kind"]
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out[:6]


def _when(wf: dict) -> str:
    """The 'Runs when' column in plain words."""
    k = wf.get("trigger_kind")
    if k == "manual":
        return "When you run it"
    if k == "webhook":
        return "As soon as data arrives"
    sp = wf.get("trigger_spec") or {}
    if k == "event":                    # v0.999.240 ROUTE R5
        from .triggers import EVENTS
        return f"{(EVENTS.get(sp.get('app')) or {}).get('title') or 'An app event'} (looks every {int(sp.get('every_minutes') or 15)} min)"
    if k == "form":
        return "When someone sends its form"
    if k == "chat":
        return "When someone writes in its chat"
    if k == "error":
        rs = sp.get("routes") or []
        return ("When " + ", ".join(str(r).replace("_", " ") for r in rs[:3]) + " fails") if rs else "When any route fails"
    if k == "route":
        return "When another route runs it"
    if k == "tool":
        return "When an AI app uses it as a tool"
    tz = sp.get("timezone") or (wf.get("settings") or {}).get("timezone") or ""
    at = ", ".join(sp.get("at") or [])
    if sp.get("once"):
        return f"Once, {str(sp['once']).replace('T', ' ')}"
    if sp.get("every_minutes"):
        return f"Every {int(sp['every_minutes'])} minutes"
    if sp.get("days"):
        return f"{' '.join(str(d).title()[:3] for d in sp['days'])}{', ' + at if at else ''}"
    if sp.get("monthdays"):
        return f"Day {', '.join(str(d) for d in sp['monthdays'])} of the month{', ' + at if at else ''}"
    if sp.get("dates"):
        return f"On {len(sp['dates'])} chosen dates"
    if at:
        return f"Every day, {at}" + (f" ({tz})" if tz else "")
    return f"Every {int(sp.get('every_hours') or 24)} hours"


def _status(wf: dict, last: dict | None) -> dict[str, str]:
    if not wf.get("enabled"):
        if int(wf.get("consecutive_errors") or 0) and (wf.get("settings") or {}).get("stop_after_errors"):
            return {"key": "stopped", "text": "Stopped after errors"}
        return {"key": "off", "text": "Off"}
    st = (last or {}).get("status")
    if st == "waiting_approval":
        return {"key": "waiting", "text": "Waiting for you"}
    if st in ("failed", "incomplete"):
        return {"key": "error", "text": "Last run failed" if st == "failed" else "Incomplete run"}
    if st in ("queued", "running", "sleeping"):
        return {"key": "running", "text": "Running"}
    if last is None:       # v0.999.128: a route that never ran is not "Working" yet
        return {"key": "off" if wf.get("trigger_kind") == "manual" else "running",
                "text": {"webhook": "Waiting for data", "schedule": "Waiting for its time"}.get(
                    wf.get("trigger_kind"), "Not run yet")}
    if st == "stopped":
        return {"key": "off", "text": "Last run stopped"}
    return {"key": "ok", "text": "Working"}


def _waiting_question(wf: dict, run: dict) -> str:
    """The question of the approval step this run is parked on (the cursor's step), not just any approval step.
    v0.999.239: an approval inside a branch or loop is named by the run itself (its question, with the data)."""
    c: dict = {}
    try:
        c = run.get("context")
        c = json.loads(c) if isinstance(c, str) else (c or {})
        if c.get("_wait_mark") and c.get("_wait_q"):
            return str(c["_wait_q"])
    except Exception:   # noqa: BLE001
        c = {}
    top = [s for s in (wf.get("steps") or []) if isinstance(s, dict)]
    try:
        cur = int(run.get("cursor") or 0)
    except (TypeError, ValueError):
        cur = 0
    def filled(q: str) -> str:
        # v0.999.253: the question with the run's own data ("Send 50 payment?", not "Send {{vars.a}} payment?")
        try:
            from ..agent import dhara_tools as D
            return str(D.resolve(q, c if isinstance(c, dict) else {}))[:400]
        except Exception:   # noqa: BLE001
            return q
    if 0 <= cur < len(top) and top[cur].get("type") == "approval":
        return filled(str(top[cur].get("question") or ""))
    for st in _walk(top[cur:] if 0 <= cur < len(top) else top):   # an approval inside a branch at the cursor
        if st.get("type") == "approval":
            return filled(str(st.get("question") or ""))
    return ""


def make_router(require_key, current_tenant) -> APIRouter:
    from ..agent import dhara_tools as D
    from ..agent.tools import Ctx, ToolError
    from . import editor as E
    r = APIRouter(prefix="/api/route", dependencies=[Depends(require_key)])

    async def run(fn, *a, **kw):
        return await asyncio.to_thread(fn, *a, **kw)

    def _wf_or_404(tenant: str, wf_id: str) -> dict:
        wf = D.get_workflow(tenant, wf_id=wf_id)
        if wf is None:
            raise HTTPException(404, "Route not found")
        return wf

    def _card(tenant: str, wf: dict) -> dict:
        last = D.latest_run(tenant, wf["id"])
        con = D._con(tenant)
        try:
            n30 = int(con.execute("SELECT COUNT(*) FROM runs WHERE workflow_id = ? AND created_at >= ?",
                                  (wf["id"], time.time() - 30 * 86400)).fetchone()[0])
        finally:
            con.close()
        return {"id": wf["id"], "name": wf["name"], "description": wf.get("description") or "", "days7": _days7(tenant, wf["id"]),
                "enabled": bool(wf.get("enabled")), "trigger": wf["trigger_kind"], "when": _when(wf),
                "folder": (wf.get("settings") or {}).get("folder") or "", "apps": apps_of(wf.get("steps") or []),
                "steps": len(_walk(wf.get("steps") or [])), "runs_30d": n30,
                "last_run": ({"id": last["id"], "status": last["status"], "at": last.get("created_at")} if last else None),
                "next_due_at": wf.get("next_due_at"), "status": _status(wf, last),
                "tags": (wf.get("settings") or {}).get("tags") or [],
                "errors_in_a_row": int(wf.get("consecutive_errors") or 0)}

    def _days7(tenant: str, wf_id: str) -> list[dict]:
        """v0.999.232: the last 7 days of this route, oldest first - runs that went well and runs that did not."""
        day0 = time.time() - 6 * 86400
        start = time.mktime(time.localtime(day0)[:3] + (0, 0, 0, 0, 0, -1))
        out = [{"ok": 0, "bad": 0} for _ in range(7)]
        con = D._con(tenant)
        try:
            for x in con.execute("SELECT status, created_at FROM runs WHERE workflow_id = ? AND created_at >= ?",
                                 (wf_id, start)).fetchall():
                i = int((float(x["created_at"]) - start) // 86400)
                if 0 <= i < 7:
                    if x["status"] in ("failed", "incomplete"):
                        out[i]["bad"] += 1
                    elif x["status"] == "done":
                        out[i]["ok"] += 1
        finally:
            con.close()
        return out

    def _summary(tenant: str) -> dict:
        wfs = D.list_workflows(tenant, 200)
        con = D._con(tenant)
        try:
            day = time.time() - 86400
            runs_today = int(con.execute("SELECT COUNT(*) FROM runs WHERE created_at >= ?", (day,)).fetchone()[0])
            week = time.time() - 7 * 86400
            runs_7d = int(con.execute("SELECT COUNT(*) FROM runs WHERE created_at >= ?", (week,)).fetchone()[0])
            failed_7d = int(con.execute("SELECT COUNT(*) FROM runs WHERE created_at >= ? AND status IN ('failed','incomplete')",
                                        (week,)).fetchone()[0])
            m30 = time.time() - 30 * 86400
            ended = con.execute("SELECT SUM(status = 'done'), SUM(status IN ('failed','incomplete')) FROM runs WHERE created_at >= ?",
                                (m30,)).fetchone()
            ok30, bad30 = int(ended[0] or 0), int(ended[1] or 0)
            # v0.999.297 ROUTE HOME REDESIGN: the week before (for "18% more than last week"), runs per day of this
            # week (the trend line) and runs per hour of the last 12 hours (the sidebar's little bars)
            runs_prev_7d = int(con.execute("SELECT COUNT(*) FROM runs WHERE created_at >= ? AND created_at < ?",
                                           (week - 7 * 86400, week)).fetchone()[0])
            now = time.time()
            week_days, hours12 = [0] * 7, [0] * 12
            for (ts,) in con.execute("SELECT created_at FROM runs WHERE created_at >= ?", (week,)).fetchall():
                ts = float(ts)
                d = int((now - ts) // 86400)
                if 0 <= d < 7:
                    week_days[6 - d] += 1
                h = int((now - ts) // 3600)
                if 0 <= h < 12:
                    hours12[11 - h] += 1
            waiting = [dict(x) for x in con.execute(
                "SELECT id, wf_name, workflow_id, cursor, updated_at, context FROM runs WHERE status = 'waiting_approval' "
                "ORDER BY updated_at DESC LIMIT 20").fetchall()]
            # v0.999.128: a failure needs her only while it is the route's LATEST run - a later good run or a
            # retry that finished clears it (the list used to keep every failure of the week)
            bad = [dict(x) for x in con.execute(
                "SELECT r.id, r.wf_name, r.workflow_id, r.status, r.error, r.updated_at FROM runs r WHERE r.status IN "
                "('incomplete','failed') AND r.updated_at >= ? AND r.created_at = (SELECT MAX(created_at) FROM runs "
                "WHERE workflow_id = r.workflow_id) ORDER BY r.updated_at DESC LIMIT 20",
                (time.time() - 7 * 86400,)).fetchall()]
        finally:
            con.close()
        needs = []
        by_id = {w["id"]: w for w in wfs}
        for w in waiting:
            wf = by_id.get(w["workflow_id"]) or {}
            q = _waiting_question(wf, w)
            needs.append({"kind": "approval", "run_id": w["id"], "route": w["wf_name"], "route_id": w["workflow_id"],
                          "text": q or "This route is waiting for your OK"})
        for b in bad:
            needs.append({"kind": b["status"], "run_id": b["id"], "route": b["wf_name"], "route_id": b["workflow_id"],
                          "text": (b.get("error") or "")[:220]})
        for wf in wfs:
            if not wf.get("enabled") and int(wf.get("consecutive_errors") or 0) and \
                    (wf.get("settings") or {}).get("stop_after_errors"):
                needs.append({"kind": "stopped", "route": wf["name"], "route_id": wf["id"],
                              "text": f"Switched off after {wf['consecutive_errors']} failed runs in a row"})
        return {"routes_total": len(wfs), "routes_on": sum(1 for w in wfs if w.get("enabled")),
                "runs_today": runs_today, "runs_7d": runs_7d, "failed_7d": failed_7d, "runs_prev_7d": runs_prev_7d,
                "week_days": week_days, "hours12": hours12,
                "success_30d": (round(100 * ok30 / (ok30 + bad30)) if ok30 + bad30 else None), "failed_30d": bad30,
                "folders": sorted({(w.get("settings") or {}).get("folder") for w in wfs} - {None, ""}),
                "needs_you": needs[:30], "needs_count": len(needs)}

    @r.get("/summary")
    async def route_summary(tenant: str = Depends(current_tenant)):
        return await run(_summary, tenant)

    @r.get("/routes")
    async def route_list(tenant: str = Depends(current_tenant)):
        def go():
            return {"routes": [_card(tenant, wf) for wf in D.list_workflows(tenant, 200)]}
        return await run(go)

    def _full(tenant: str, wf: dict) -> dict:
        out = _card(tenant, wf)
        steps = wf.get("steps") or []

        def deco(lst):
            res = []
            for s in lst or []:
                if not isinstance(s, dict):
                    continue
                d = {k: v for k, v in s.items() if k not in ("then", "else", "fallback", "routes")
                     and not (k == "body" and s.get("type") == "loop")}
                d["app"] = app_of(s)
                for k in ("then", "else", "body", "fallback"):
                    if isinstance(s.get(k), list) and (k != "body" or s.get("type") == "loop"):
                        d[k] = deco(s[k])
                if s.get("routes"):
                    d["routes"] = [{**{k: v for k, v in rt.items() if k != "steps"}, "steps": deco(rt.get("steps"))}
                                   for rt in s["routes"] if isinstance(rt, dict)]
                if isinstance(s.get("on_error"), dict) and isinstance(s["on_error"].get("steps"), list):
                    d["on_error"] = {**s["on_error"], "steps": deco(s["on_error"]["steps"])}
                res.append(d)
            return res
        out["graph"] = D._masked(deco(steps))
        out["trigger_spec"] = wf.get("trigger_spec") or {}
        out["settings"] = wf.get("settings") or {}
        from . import triggers as TR                 # v0.999.240 ROUTE R5: what the trigger panel shows
        out["public_url"] = TR.public_address(tenant, wf)
        if wf.get("trigger_kind") == "event":
            out["poll"] = TR.poll_state(tenant, wf["id"])
        from . import workspace as WS                # v0.999.246 ROUTE R7
        out["share"] = WS.share_state(tenant, wf["id"])
        m = E.meta(tenant, wf["id"])
        out["layout"] = {"pos": m["pos"], "notes": m["notes"]}
        out["version"] = wf.get("updated_at")
        return out

    @r.get("/routes/{wf_id}")
    async def route_one(wf_id: str, tenant: str = Depends(current_tenant)):
        return await run(lambda: _full(tenant, _wf_or_404(tenant, wf_id)))

    # ---------------------------------------------------------------- v0.999.232 the editor
    @r.post("/routes")
    async def route_new(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """A new route made from the page: OFF, with one placeholder step, ready for the canvas or Ask Hoola."""
        def go():
            try:
                wf = E.new_route(tenant, str((body or {}).get("title") or "New route")[:120], str((body or {}).get("folder") or ""))
            except ToolError as e:
                raise HTTPException(400, str(e))
            return _full(tenant, wf)
        return await run(go)

    @r.put("/routes/{wf_id}/graph")
    async def route_graph(wf_id: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        def go():
            wf = _wf_or_404(tenant, wf_id)
            try:
                new = E.save_graph(tenant, wf, body or {})
            except ToolError as e:
                raise HTTPException(400, str(e))
            except ValueError as e:
                if str(e) == "conflict":
                    raise HTTPException(409, "This route changed since you opened it (Hoola or another tab saved it). "
                                             "Reload to see the new version, then make your change again.")
                raise HTTPException(400, str(e))
            return _full(tenant, new)
        return await run(go)

    @r.put("/routes/{wf_id}/layout")
    async def route_layout(wf_id: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        def go():
            wf = _wf_or_404(tenant, wf_id)
            try:
                return E.save_layout(tenant, wf["id"], body or {})
            except ValueError as e:
                raise HTTPException(400, str(e))
        return await run(go)

    @r.post("/routes/{wf_id}/test")
    async def route_test(wf_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Test route: one real run now, even while the route is switched off (the editor's Test button)."""
        from . import stepdata as SD
        wf = await run(_wf_or_404, tenant, wf_id)
        vars_ = (body or {}).get("vars")
        v0 = vars_ if isinstance(vars_, dict) else {}
        extra = None
        # v0.999.234 R2: a test starts with her pinned test data, and pinned steps give their pinned output
        # v0.999.253: written WITH the run - the worker could pick it up in between and run real steps unpinned
        if (body or {}).get("use_pins", True):
            pc = await run(SD.context_for, tenant, wf, True)
            if not isinstance(vars_, dict):
                v0 = (await run(SD.pins, tenant, wf["id"])).get("trigger") or {}
            extra = {"_pins": pc.get("_pins") or {}}
        rid = await run(lambda: D.create_run(tenant, wf, v0, extra=extra))
        D._start_now(tenant, rid)               # claimed first (on the event loop: it starts the task)
        return {"run_id": rid, "status": "queued"}

    # ---------------------------------------------------------------- v0.999.234 R2: step data, single-step tests, pins
    @r.get("/routes/{wf_id}/data")
    async def route_data(wf_id: str, run_id: str = "", tenant: str = Depends(current_tenant)):
        """The route's newest data, or (R8, ?run_id=) one past run's data for debugging it in the editor."""
        from . import stepdata as SD

        def go():
            try:
                return D._masked(SD.data(tenant, _wf_or_404(tenant, wf_id), str(run_id or "")[:40]))
            except ValueError as e:
                raise HTTPException(404, str(e))
        return await run(go)

    @r.post("/routes/{wf_id}/steps/{sid}/test")
    async def route_step_test(wf_id: str, sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Test one step on the route's newest data (and her pins), or on a past run's data (R8, run_id).
        A step that sends or writes really does it."""
        from . import stepdata as SD
        wf = await run(_wf_or_404, tenant, wf_id)
        try:
            return await SD.test_step(tenant, wf, sid, bool((body or {}).get("use_pins", True)),
                                      str((body or {}).get("run_id") or "")[:40])
        except ValueError as e:
            raise HTTPException(400, str(e))

    @r.post("/routes/{wf_id}/eval")
    async def route_eval(wf_id: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        """v0.999.237 R3: what a box becomes with the route's newest data (the editor's live result line)."""
        from . import stepdata as SD

        def go():
            try:
                return SD.preview(tenant, _wf_or_404(tenant, wf_id), str((body or {}).get("text") or ""),
                                  str((body or {}).get("step") or ""), str((body or {}).get("run_id") or "")[:40])
            except ValueError as e:
                raise HTTPException(404, str(e))
        return await run(go)

    @r.post("/routes/{wf_id}/pins/from-run")
    async def route_pins_from_run(wf_id: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        """v0.999.248 R8: pin a past run's start data and step outputs, so tests work on that exact data."""
        from . import runs as RU

        def go():
            wf = _wf_or_404(tenant, wf_id)
            steps = (body or {}).get("steps")
            try:
                return RU.pin_from_run(tenant, wf, str((body or {}).get("run_id") or ""),
                                       [str(x) for x in steps] if isinstance(steps, list) else None,
                                       bool((body or {}).get("trigger", True)))
            except RU.RunsError as e:
                raise HTTPException(404, str(e))
        return await run(go)

    @r.get("/insights")
    async def route_insights(days: int = 7, route_id: str = "", tz: str = "UTC", tenant: str = Depends(current_tenant)):
        """v0.999.248 R8: how her routes do - runs, failures, working time, slow and failing steps, time saved."""
        from . import runs as RU
        return await run(RU.insights, tenant, days, str(route_id or "")[:40], str(tz or "UTC")[:60])

    @r.put("/routes/{wf_id}/pins/{sid}")
    async def route_pin(wf_id: str, sid: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        from . import stepdata as SD

        def go():
            wf = _wf_or_404(tenant, wf_id)
            if "value" not in (body or {}):
                raise HTTPException(400, "Send the data to pin as value")
            try:
                return {"pins": list(SD.set_pin(tenant, wf, sid, body["value"]))}
            except ValueError as e:
                raise HTTPException(400, str(e))
        return await run(go)

    @r.delete("/routes/{wf_id}/pins/{sid}")
    async def route_unpin(wf_id: str, sid: str, tenant: str = Depends(current_tenant)):
        from . import stepdata as SD
        return await run(lambda: {"pins": list(SD.drop_pin(tenant, _wf_or_404(tenant, wf_id)["id"], sid))})

    @r.get("/routes/{wf_id}/chat")
    async def route_chat(wf_id: str, tenant: str = Depends(current_tenant)):
        from . import chat as RC
        return await run(lambda: RC.chat_for(tenant, _wf_or_404(tenant, wf_id)))

    @r.get("/catalog")
    async def route_catalog(q: str = ""):
        return {"kinds": E.KINDS, "tools": await run(E.tools, q[:120])}

    @r.get("/catalog/tool/{name}")
    async def route_catalog_tool(name: str):
        t = await run(E.tool_one, name[:80])
        if t is None:
            raise HTTPException(404, "No such tool")
        return t

    # v0.999.278 SENDING: what a route sends, her tap that allows it, and a Telegram bot that starts it
    @r.get("/routes/{wf_id}/sending")
    async def route_sending(wf_id: str, tenant: str = Depends(current_tenant)):
        from . import send as SN
        return await run(lambda: SN.status(tenant, _wf_or_404(tenant, wf_id)))

    @r.post("/routes/{wf_id}/sending")
    async def route_sending_allow(wf_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from . import send as SN

        def go():
            try:
                return SN.allow(tenant, _wf_or_404(tenant, wf_id), str((body or {}).get("hash") or ""),
                                bool((body or {}).get("allow", True)))
            except SN.SendError as e:
                raise HTTPException(409, str(e))
        return await run(go)

    @r.post("/routes/{wf_id}/bot")
    async def route_bot(wf_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        from ..config import get_settings
        from . import send as SN
        from . import workspace as WS

        def go():
            wf = _wf_or_404(tenant, wf_id)
            base = str(getattr(get_settings(), "public_base_url", "") or "")
            try:
                return SN.connect_bot(tenant, wf, str((body or {}).get("connection") or ""), base)
            except (SN.SendError, WS.WorkspaceError) as e:
                raise HTTPException(400, str(e))
        return await run(go)

    @r.delete("/routes/{wf_id}/bot")
    async def route_bot_drop(wf_id: str, tenant: str = Depends(current_tenant)):
        from . import send as SN
        return await run(lambda: SN.disconnect_bot(tenant, _wf_or_404(tenant, wf_id)))

    @r.post("/routes/{wf_id}/switch")
    async def route_switch(wf_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        def go():
            wf = _wf_or_404(tenant, wf_id)
            on = bool((body or {}).get("on"))
            D.set_enabled(tenant, wf["id"], on)
            if on:   # a fresh start: the errors-in-a-row count begins again
                con = D._con(tenant)
                try:
                    con.execute("UPDATE workflows SET consecutive_errors = 0 WHERE id = ?", (wf["id"],))
                    if wf.get("trigger_kind") == "schedule":
                        con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?", (D.next_due(wf), wf["id"]))
                    con.commit()
                finally:
                    con.close()
            return {"id": wf["id"], "enabled": on}
        return await run(go)

    async def _tool(tenant: str, fn, **kw):
        try:
            return await fn(Ctx(tenant_id=tenant, conversation_id=""), **kw)
        except ToolError as e:
            raise HTTPException(400, str(e))

    @r.post("/routes/{wf_id}/run")
    async def route_run(wf_id: str, tenant: str = Depends(current_tenant)):
        await run(_wf_or_404, tenant, wf_id)
        return await _tool(tenant, D.dhara_run, workflow_id=wf_id)

    @r.get("/runs")
    async def route_runs(workflow_id: str = "", status: str = "", limit: int = 30, q: str = "",
                         tenant: str = Depends(current_tenant)):
        def go():
            if str(q or "").strip():          # v0.999.248 R8: runs that hold a value anywhere in their data
                from . import runs as RU
                try:
                    return RU.search(tenant, q, workflow_id, status, limit)
                except RU.RunsError as e:
                    raise HTTPException(400, str(e))
            rows = D.list_runs(tenant, wf_id=workflow_id, limit=max(1, min(int(limit or 30), 100)), status=status)
            return {"runs": D._masked([{"id": x["id"], "route": x["wf_name"], "route_id": x["workflow_id"],
                                        "status": x["status"], "steps_done": x["cursor"], "error": (x.get("error") or "")[:300],
                                        "pause_reason": x.get("pause_reason") or "", "summary": x.get("summary"),
                                        "at": x.get("created_at"), "next_wake_at": x.get("next_wake_at")} for x in rows])}
        return await run(go)

    def _start_of(x: dict) -> Any:
        from . import runs as RU
        from . import stepdata as SD
        return SD._view(RU.start_data(x))

    def _failed_of(x: dict) -> str:
        from . import runs as RU
        return RU.failed_step(x)

    def _outputs(x: dict) -> dict:
        from . import stepdata as SD
        out, total = {}, 0
        for k, v in ((x.get("context") or {}).get("steps") or {}).items():
            if not isinstance(v, dict):
                continue
            val = SD._view(v.get("output"))
            total += SD._size(val)
            if total > 600_000:
                break
            out[k] = val
        return out

    @r.get("/runs/{run_id}")
    async def route_run_one(run_id: str, tenant: str = Depends(current_tenant)):
        def go():
            x = D.get_run(tenant, run_id)
            if x is None:
                raise HTTPException(404, "Run not found")
            return D._masked({"id": x["id"], "route": x["wf_name"], "route_id": x["workflow_id"], "status": x["status"],
                              "error": x.get("error") or "", "pause_reason": x.get("pause_reason") or "",
                              "summary": x.get("summary"), "steps_log": (x.get("steps_log") or [])[-300:],
                              # v0.999.234 R2: each step's whole output (the log keeps 600 characters of it)
                              "outputs": _outputs(x), "pinned": sorted(((x.get("context") or {}).get("_pins") or {}).keys()),
                              # v0.999.248 R8: what it started with + where it failed (Run again / Debug)
                              "start": _start_of(x), "failed_step": _failed_of(x),
                              "at": x.get("created_at"), "next_wake_at": x.get("next_wake_at")})
        return await run(go)

    @r.post("/runs/{run_id}/rerun")
    async def route_rerun(run_id: str, tenant: str = Depends(current_tenant)):
        """v0.999.248 R8: Run again - a new run with the data this run started with (the old one stays)."""
        from . import runs as RU
        try:
            out = await run(RU.rerun, tenant, run_id)
        except RU.RunsError as e:
            raise HTTPException(404 if "not found" in str(e).lower() or "gone" in str(e) else 409, str(e))
        D._start_now(tenant, out["run_id"])     # v0.999.253: claimed first, never twice
        return out

    @r.post("/runs/{run_id}/{action}")
    async def route_run_act(run_id: str, action: str, tenant: str = Depends(current_tenant)):
        if action not in ("approve", "stop", "retry"):
            raise HTTPException(404, "Unknown action")
        x = await run(D.get_run, tenant, run_id)
        if x is None:
            raise HTTPException(404, "Run not found")
        res = await _tool(tenant, D.dhara_control, action=action, run_id=run_id)
        # v0.999.128: the engine answers "not done" with a note (already stopped, not waiting, approval expired);
        # the page used to say "Approved" / "Retrying" anyway. Only the state the tap asked for is success.
        want = {"approve": "queued", "retry": "queued", "stop": "stopped"}[action]
        if not isinstance(res, dict) or res.get("ok") is False or res.get("status") != want:
            raise HTTPException(409, str((res or {}).get("note") or "That could not be done right now"))
        return res

    @r.post("/routes/{wf_id}/address")
    async def route_address(wf_id: str, tenant: str = Depends(current_tenant)):
        """v0.999.128: the address that starts a webhook route. Only its hash is kept, so a NEW address is made
        here and shown once; the old one stops working at that moment (the page says so before her tap)."""
        from ..config import get_settings

        def go():
            from . import triggers as TR
            wf = _wf_or_404(tenant, wf_id)
            if wf.get("trigger_kind") not in TR.TOKEN_KINDS:
                raise HTTPException(400, "This route is not started from an address")
            _ = get_settings
            return TR.make_address(tenant, wf)       # v0.999.240: a form / chat page's address too
        return await run(go)

    @r.delete("/routes/{wf_id}")
    async def route_delete(wf_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """v0.999.128: delete a route on her tap. The page asks first and sends the route's name back as the
        confirmation; a route with a run in progress is refused (stop the run first)."""
        def go():
            wf = _wf_or_404(tenant, wf_id)
            if str((body or {}).get("confirm") or "") != wf["name"]:
                raise HTTPException(400, "Confirm with the route's name")
            con = D._con(tenant)
            try:
                busy = con.execute("SELECT COUNT(*) FROM runs WHERE workflow_id = ? AND status IN "
                                   "('queued','running','sleeping','waiting_approval')", (wf["id"],)).fetchone()[0]
                if busy:
                    raise HTTPException(409, "A run of this route is still going - stop it first")
                con.execute("DELETE FROM runs WHERE workflow_id = ?", (wf["id"],))
                con.execute("DELETE FROM workflows WHERE id = ?", (wf["id"],))
                con.commit()
            finally:
                con.close()
            E.forget(tenant, wf["id"])
            return {"deleted": wf["id"], "name": wf["name"]}
        return await run(go)

    # ---------------------------------------------------------------- v0.999.246 ROUTE R7: accounts, variables, sign-ins,
    # settings, versions, sharing
    from . import workspace as WS

    def _ws(fn, *a):
        try:
            return fn(*a)
        except WS.WorkspaceError as e:
            raise HTTPException(400, str(e))
        except ToolError as e:
            raise HTTPException(400, str(e))

    @r.get("/variables")
    async def route_vars(tenant: str = Depends(current_tenant)):
        return {"variables": await run(WS.variables, tenant)}

    @r.put("/variables/{name}")
    async def route_var_set(name: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await run(_ws, WS.set_variable, tenant, name, (body or {}).get("value"), str((body or {}).get("note") or ""))

    @r.delete("/variables/{name}")
    async def route_var_drop(name: str, tenant: str = Depends(current_tenant)):
        await run(WS.drop_variable, tenant, name)
        return {"deleted": name}

    @r.get("/credentials")
    async def route_creds(tenant: str = Depends(current_tenant)):
        """Her saved sign-ins: names, kinds, sites and the last 4 - never the secret itself."""
        return {"credentials": await run(WS.credentials, tenant), "kinds": list(WS.CRED_KINDS)}

    @r.post("/credentials")
    async def route_cred_save(body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await run(_ws, WS.save_credential, tenant, body or {})

    @r.delete("/credentials/{name}")
    async def route_cred_drop(name: str, tenant: str = Depends(current_tenant)):
        await run(WS.drop_credential, tenant, name)
        return {"deleted": name}

    @r.get("/accounts")
    async def route_accounts(tenant: str = Depends(current_tenant)):
        return {"accounts": await run(WS.accounts, tenant)}

    @r.get("/team")
    async def route_team(tenant: str = Depends(current_tenant)):
        def go():
            try:
                from ..employee import service as ES
                return [{"id": m["id"], "name": m["name"], "role": m["role"], "active": m["active"]} for m in ES.team(tenant)]
            except Exception:   # noqa: BLE001
                return []
        return {"team": await run(go)}

    @r.put("/routes/{wf_id}/settings")
    async def route_settings(wf_id: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        """Every route setting from the page: folder, tags, time zone, switch off after errors, error route, runs a day,
        currency, the description and the team members who may run it."""
        def go():
            wf = _wf_or_404(tenant, wf_id)
            b = dict(body or {})
            desc = str(b.pop("description", wf.get("description") or ""))[:500]
            settings = _ws(D.validate_settings, b, tenant)
            er = settings.get("error_route")
            if er and (er == wf["name"] or D.get_workflow(tenant, name=er) is None):
                raise HTTPException(400, "The error route must be another of your routes")
            new, _ = D.save_workflow(tenant, wf["name"], desc, wf["trigger_kind"], wf.get("trigger_spec") or {}, wf.get("steps") or [],
                                     settings=settings, note="Settings changed")
            if new["trigger_kind"] == "schedule":
                con = D._con(tenant)
                try:
                    con.execute("UPDATE workflows SET next_due_at = ? WHERE id = ?", (D.next_due(new), new["id"]))
                    con.commit()
                finally:
                    con.close()
            return _full(tenant, D.get_workflow(tenant, wf_id=new["id"]))
        return await run(go)

    @r.get("/routes/{wf_id}/versions")
    async def route_versions(wf_id: str, tenant: str = Depends(current_tenant)):
        wf = await run(_wf_or_404, tenant, wf_id)
        return {"versions": await run(WS.versions, tenant, wf["id"])}

    @r.get("/routes/{wf_id}/versions/{vid}")
    async def route_version(wf_id: str, vid: str, tenant: str = Depends(current_tenant)):
        wf = await run(_wf_or_404, tenant, wf_id)
        v = await run(WS.version, tenant, wf["id"], vid)
        if v is None:
            raise HTTPException(404, "That version is not kept any more")
        return D._masked(v)

    @r.post("/routes/{wf_id}/versions/{vid}/restore")
    async def route_restore(wf_id: str, vid: str, tenant: str = Depends(current_tenant)):
        def go():
            wf = _wf_or_404(tenant, wf_id)
            return _full(tenant, _ws(WS.restore, tenant, wf, vid))
        return await run(go)

    @r.post("/routes/{wf_id}/share")
    async def route_share(wf_id: str, tenant: str = Depends(current_tenant)):
        """A read-only link to look at this route (its steps in words; no data, no sign-ins) for 30 days."""
        wf = await run(_wf_or_404, tenant, wf_id)
        return await run(WS.share_make, tenant, wf["id"])

    @r.delete("/routes/{wf_id}/share")
    async def route_share_stop(wf_id: str, tenant: str = Depends(current_tenant)):
        wf = await run(_wf_or_404, tenant, wf_id)
        await run(WS.share_stop, tenant, wf["id"])
        return {"on": False}

    @r.get("/routes/{wf_id}/export")
    async def route_export(wf_id: str, tenant: str = Depends(current_tenant)):
        """The route as a file (keys and addresses left out) to keep or bring into another account."""
        wf = await run(_wf_or_404, tenant, wf_id)
        return await run(D.dsl_export, tenant, wf)

    @r.post("/import/n8n")
    async def route_import_n8n(body: dict = Body(...), tenant: str = Depends(current_tenant)):
        """v0.999.248 R8: bring in an n8n workflow. save=false = the route it would become + the report only;
        save=true = a new route, switched off (a name that is taken is refused, never overwritten)."""
        from . import n8n as N8
        raw = (body or {}).get("workflow")
        if raw in (None, ""):
            raise HTTPException(400, "Paste the n8n workflow (its exported JSON)")

        def go():
            try:
                if not (body or {}).get("save"):
                    return D._masked(N8.convert(raw))
                return N8.bring_in(tenant, raw, str((body or {}).get("new_name") or ""))
            except N8.N8nError as e:
                raise HTTPException(409 if "already there" in str(e) else 400, str(e))
        return await run(go)

    # v0.999.264 THE WORKFLOW LIBRARY: ready-made n8n workflows (github.com/Zie619/n8n-workflows, MIT, one fixed commit)
    @r.get("/library")
    async def route_library(q: str = "", category: str = "", app: str = "", trigger: str = "", ready: str = "",
                            page: int = 1, per: int = 24, tenant: str = Depends(current_tenant)):
        from . import n8nlib as L
        return L.search(q[:200], category[:80], app[:80], trigger[:20], ready[:10], page, per)

    @r.get("/library/{wid}")
    async def route_library_one(wid: str, tenant: str = Depends(current_tenant)):
        """What one library workflow becomes in Hoola - fetched from GitHub once, checked, keys taken out; nothing saved."""
        from . import n8n as N8, n8nlib as L

        def go():
            try:
                return D._masked(L.preview(wid))
            except (L.LibError, N8.N8nError) as e:
                raise HTTPException(404 if "not in the library" in str(e) else 502, str(e))
        return await run(go)

    @r.post("/library/{wid}/use")
    async def route_library_use(wid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        """Bring a library workflow in as a new route, switched off (a taken name is refused, never overwritten)."""
        from . import n8n as N8, n8nlib as L

        def go():
            try:
                return L.use(tenant, wid, str((body or {}).get("new_name") or ""))
            except L.LibError as e:
                raise HTTPException(404 if "not in the library" in str(e) else 502, str(e))
            except N8.N8nError as e:
                raise HTTPException(409 if "already there" in str(e) else 400, str(e))
        return await run(go)

    @r.post("/import")
    async def route_import(body: dict = Body(...), tenant: str = Depends(current_tenant)):
        """Bring in a route file: the engine's own checks, and it lands switched off."""
        out = await D.dhara_dsl(Ctx(tenant_id=tenant, conversation_id=""), action="import", dsl=(body or {}).get("dsl"),
                                new_name=str((body or {}).get("new_name") or ""))
        if not out.get("ok"):
            raise HTTPException(409, out.get("note") or "That route name is taken")
        return out

    # ---------------------------------------------------------------- v0.999.240 ROUTE R5 triggers
    @r.get("/triggers")
    async def route_triggers(tenant: str = Depends(current_tenant)):
        """What the trigger panel offers: the app events and the MCP address state."""
        from . import triggers as TR
        return {"events": [{"key": k, "title": v["title"]} for k, v in TR.EVENTS.items()],
                "form_types": list(TR.FORM_TYPES), "mcp": await run(TR.mcp_state, tenant),
                "every": {"min": TR.EVERY_MIN, "max": TR.EVERY_MAX, "default": TR.EVERY_DEFAULT}}

    @r.post("/mcp")
    async def route_mcp(tenant: str = Depends(current_tenant)):
        """Her MCP address: her routes started 'as a tool' become tools an AI app can call. Shown once."""
        from . import triggers as TR
        return await run(TR.mcp_key, tenant)

    @r.post("/routes/{wf_id}/look")
    async def route_look(wf_id: str, tenant: str = Depends(current_tenant)):
        """Look for new items now (an app-event route); the first look only notes what is there."""
        from . import triggers as TR
        wf = await run(_wf_or_404, tenant, wf_id)
        if wf.get("trigger_kind") != "event":
            raise HTTPException(400, "This route is not started by an app event")
        out = await TR.poll(tenant, wf)
        return {**out, "poll": await run(TR.poll_state, tenant, wf["id"])}

    @r.get("/templates")
    async def route_templates():
        return {"templates": TEMPLATES}

    # ---------------------------------------------------------------- v0.999.254 MAKE PARITY: data stores
    from . import store as DS

    def _ds(fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except DS.StoreError as e:
            raise HTTPException(404 if "There is no data store" in str(e) else 400, str(e))

    @r.get("/stores")
    async def ds_list(tenant: str = Depends(current_tenant)):
        return {"stores": await run(DS.stores, tenant), "types": list(DS.TYPES),
                "limits": {"stores": DS.STORES_MAX, "max_kb": DS.SIZE_MAX_KB, "record_kb": DS.RECORD_MAX // 1024}}

    @r.put("/stores/{name}")
    async def ds_save(name: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        b = body or {}
        return await run(_ds, DS.save_store, tenant, name, b.get("structure"), b.get("max_kb"), str(b.get("note") or ""))

    @r.delete("/stores/{name}")
    async def ds_drop(name: str, tenant: str = Depends(current_tenant)):
        await run(_ds, DS.drop_store, tenant, name)
        return {"deleted": name}

    @r.get("/stores/{name}/records")
    async def ds_records(name: str, q: str = "", sort: str = "", order: str = "asc", limit: int = 100, offset: int = 0,
                         tenant: str = Depends(current_tenant)):
        def go():
            s = DS.get_store(tenant, name)
            if s is None:
                raise HTTPException(404, "There is no such data store")
            rows, total = _ds(DS.records, tenant, name, None, sort, order, DS.SEARCH_MAX, 0)
            if q.strip():
                ql = q.strip().lower()
                rows = [x for x in rows if ql in x["key"].lower() or ql in json.dumps(x["data"], ensure_ascii=False).lower()]
                total = len(rows)
            return {"store": s, "records": rows[max(0, offset):max(0, offset) + max(1, min(limit, 500))], "total": total}
        return await run(go)

    @r.put("/stores/{name}/records/{key}")
    async def ds_put(name: str, key: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await run(_ds, DS.put, tenant, name, key, (body or {}).get("data") or {})

    @r.post("/stores/{name}/records")
    async def ds_add(name: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        import uuid as _u
        k = str((body or {}).get("key") or "").strip() or str(_u.uuid4())
        return await run(_ds, DS.put, tenant, name, k, (body or {}).get("data") or {})

    @r.delete("/stores/{name}/records/{key}")
    async def ds_del(name: str, key: str, tenant: str = Depends(current_tenant)):
        return {"deleted": await run(_ds, DS.remove, tenant, name, key)}

    @r.post("/stores/{name}/clear")
    async def ds_clear(name: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        if str((body or {}).get("confirm") or "") != name:
            raise HTTPException(400, "Type the data store's name to delete every record")
        return {"deleted": await run(_ds, DS.clear, tenant, name)}

    @r.get("/stores/{name}/csv")
    async def ds_csv(name: str, tenant: str = Depends(current_tenant)):
        from fastapi.responses import Response as _R
        text = await run(_ds, DS.export_csv, tenant, name)
        return _R(text, media_type="text/csv; charset=utf-8",
                  headers={"Content-Disposition": f'attachment; filename="{DS._name(name)}.csv"'})

    @r.post("/stores/{name}/csv")
    async def ds_csv_in(name: str, body: dict = Body(...), tenant: str = Depends(current_tenant)):
        return await run(_ds, DS.import_csv, tenant, name, str((body or {}).get("csv") or ""))

    # ---------------------------------------------------------------- v0.999.254: a Make blueprint, and the Grid
    @r.post("/import/make")
    async def route_import_make(body: dict = Body(...), tenant: str = Depends(current_tenant)):
        """Bring in a Make scenario (its blueprint JSON). save=false = the route it would become + the report;
        save=true = a new route, switched off."""
        from . import makeimport as MI
        raw = (body or {}).get("blueprint")
        if raw in (None, ""):
            raise HTTPException(400, "Paste the Make scenario (Export blueprint, its JSON)")

        def go():
            try:
                if not (body or {}).get("save"):
                    return D._masked(MI.convert(raw))
                return MI.bring_in(tenant, raw, str((body or {}).get("new_name") or ""))
            except MI.MakeError as e:
                raise HTTPException(409 if "already there" in str(e) else 400, str(e))
        return await run(go)

    @r.get("/grid")
    async def route_grid(tenant: str = Depends(current_tenant)):
        """Make Grid: every route and what it touches - the routes it runs, its error route, the routes that start it,
        its data stores, apps and webhooks - as nodes and links for the map page."""
        from . import grid as G
        return await run(G.build, tenant)

    return r


# Ready-made starting points. Each is the words handed to Hoola in a chat: Hoola builds the route with the user's own
# apps, time zone and currency (nothing here assumes a country).
TEMPLATES: list[dict[str, Any]] = [
    {"id": "order_receipt", "category": "Shop", "title": "New order → WhatsApp receipt + sheet row",
     "apps": ["whatsapp", "googlesheets"],
     "ask": "Build a route: every time a new order comes in, send the customer a WhatsApp receipt and add a row to my orders sheet."},
    {"id": "invoice_reminders", "category": "Accounts", "title": "Unpaid invoice reminders every morning",
     "apps": ["googlesheets", "whatsapp"],
     "ask": "Build a route: every weekday at 10:00 my time, find unpaid invoices in my sheet and send each customer a polite reminder after I approve the list."},
    {"id": "supplier_bill", "category": "Accounts", "title": "Supplier invoice in Gmail → bill in QuickBooks",
     "apps": ["gmail", "quickbooks", "googledrive"],
     "ask": "Build a route: whenever a supplier invoice arrives in Gmail, read the amount and tax from the PDF, create a bill in my accounting app and save the PDF to Drive. Ask me first if it is over 5,000 in my currency."},
    {"id": "lead_callback", "category": "Sales", "title": "Website lead → call-back task tomorrow",
     "apps": ["googlecalendar"],
     "ask": "Build a route: when a new lead fills my website form, score it and put a call-back slot on my calendar for the next working day at 11:00."},
    {"id": "review_reply", "category": "Marketing", "title": "New Google review → thank-you reply draft",
     "apps": ["google"],
     "ask": "Build a route: for every new Google review, draft a thank-you reply. Reviews with 1-2 stars come to me first."},
    {"id": "weekly_tax", "category": "Accounts", "title": "Monday sales and tax summary to your accountant",
     "apps": ["googlesheets", "gmail"],
     "ask": "Build a route: every Monday at 09:00 my time, make a summary of last week's sales and tax as a sheet and email it to my accountant after I check it."},
    {"id": "daily_brief", "category": "Office", "title": "Morning brief of email, calendar and tasks",
     "apps": ["gmail", "googlecalendar"],
     "ask": "Build a route: every weekday at 08:30 my time, send me a short brief of today's meetings, important unread emails and open tasks."},
    {"id": "form_to_crm", "category": "Sales", "title": "Form answers → CRM contact + welcome email",
     "apps": ["hubspot", "gmail"],
     "ask": "Build a route: when someone fills my signup form, add them to my CRM and send a welcome email after I approve the text once."},
]
